"""Entry point of the packaged MCP server (GoogleFormToolMcp.exe).

Kept at the repository root, like wsgi.py, so PyInstaller analyses it as a
script while app.mcp_server stays an importable module.
"""

from app.mcp_server import main

if __name__ == "__main__":
    main()
