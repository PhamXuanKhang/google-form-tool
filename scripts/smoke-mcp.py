"""Smoke test of the packaged backend and MCP server.

Starts dist/GoogleFormTool/GoogleFormTool.exe on a port, then drives
GoogleFormToolMcp.exe over a pipe: initialize, tools/list, tools/call
app_status. Every stdout line of the MCP server must be JSON-RPC 2.0.
Both processes use a temporary APPDATA so the user's data and runtime file
are never touched. Exits non-zero on any failure.

Usage: uv run python scripts/smoke-mcp.py [--port 5056] [--dist dist/GoogleFormTool]
       uv run python scripts/smoke-mcp.py --from-source   (wsgi.py + python -m app.mcp_server)
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

EXPECTED_TOOLS = {
    "app_status", "list_forms", "extract_form", "get_form", "set_answer_config", "simulate",
    "start_run", "run_status", "stop_run", "list_runs", "get_report", "retry_failed",
    "apply_preset", "export_config", "import_config", "list_templates",
}


def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_for_health(port, timeout=60):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with opener.open(f"http://127.0.0.1:{port}/healthz", timeout=2) as response:
                if response.status == 200:
                    return json.loads(response.read())
        except OSError:
            time.sleep(0.5)
    raise SystemExit(f"backend did not answer /healthz on port {port}")


def send(process, message):
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def read_response(process, request_id, lines, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = process.stdout.readline()
        if not line:
            raise SystemExit("MCP server closed stdout early")
        lines.append(line)
        message = json.loads(line)  # any non-JSON stdout line fails here
        if message.get("jsonrpc") != "2.0":
            raise SystemExit(f"stdout line is not JSON-RPC 2.0: {line!r}")
        if message.get("id") == request_id:
            if "error" in message:
                raise SystemExit(f"request {request_id} failed: {message['error']}")
            return message["result"]
    raise SystemExit(f"no response to request {request_id}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5056)
    parser.add_argument("--dist", default="dist/GoogleFormTool")
    parser.add_argument("--from-source", action="store_true", help="run wsgi.py and python -m app.mcp_server")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if args.from_source:
        backend_cmd = [sys.executable, str(repo_root / "wsgi.py")]
        mcp_cmd = [sys.executable, "-m", "app.mcp_server"]
    else:
        dist = Path(args.dist).resolve()
        backend_cmd = [str(dist / "GoogleFormTool.exe")]
        mcp_cmd = [str(dist / "GoogleFormToolMcp.exe")]
        for exe in (backend_cmd[0], mcp_cmd[0]):
            if not Path(exe).exists():
                raise SystemExit(f"missing {exe}")
    if port_in_use(args.port):
        raise SystemExit(f"port {args.port} is already in use")

    with tempfile.TemporaryDirectory(prefix="gft-smoke-") as app_data:
        env = dict(os.environ, APPDATA=app_data, PORT=str(args.port), GOOGLE_FORM_TOOL_NO_BROWSER="1")
        backend = subprocess.Popen(backend_cmd, env=env, cwd=repo_root,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        mcp = None
        try:
            print("healthz:", wait_for_health(args.port))
            mcp = subprocess.Popen(mcp_cmd, env=env, cwd=repo_root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, encoding="utf-8")
            lines = []
            send(mcp, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {},
                "clientInfo": {"name": "smoke", "version": "1"}}})
            init = read_response(mcp, 1, lines)
            send(mcp, {"jsonrpc": "2.0", "method": "notifications/initialized"})
            send(mcp, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            tools = {tool["name"] for tool in read_response(mcp, 2, lines)["tools"]}
            send(mcp, {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                       "params": {"name": "app_status", "arguments": {}}})
            status = read_response(mcp, 3, lines)
            mcp.stdin.close()
            mcp.wait(timeout=15)
            mcp = None

            print("server:", init.get("serverInfo"))
            print("tools:", sorted(tools))
            if tools != EXPECTED_TOOLS:
                raise SystemExit(f"tool list mismatch: missing {EXPECTED_TOOLS - tools}, extra {tools - EXPECTED_TOOLS}")
            if status.get("isError"):
                raise SystemExit(f"app_status failed: {status}")
            app_status = json.loads(status["content"][0]["text"])
            print("app_status:", app_status)
            if not app_status.get("version"):
                raise SystemExit("app_status returned no version")
            print(f"stdout lines checked: {len(lines)}, all JSON-RPC 2.0")
        finally:
            if mcp is not None:
                mcp.kill()
            backend.terminate()
            try:
                backend.wait(timeout=15)
            except subprocess.TimeoutExpired:
                backend.kill()
                backend.wait(timeout=15)
        time.sleep(1)
        if port_in_use(args.port):
            raise SystemExit(f"port {args.port} still in use after stopping the backend")
    print("MCP smoke: OK")


if __name__ == "__main__":
    sys.exit(main())
