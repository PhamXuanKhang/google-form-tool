const { spawn } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_PORT = 5123;
const STARTUP_LOG_LIMIT = 4000;

let backendProcess = null;
let recentOutput = '';

function appendOutput(chunk) {
  recentOutput = `${recentOutput}${chunk.toString()}`.slice(-STARTUP_LOG_LIMIT);
}

function getBackendUrl(port) {
  return `http://127.0.0.1:${port}`;
}

function getPackagedBackendPath() {
  return path.join(process.resourcesPath, 'backend', 'GoogleFormTool.exe');
}

function startBackend({ appPath, isPackaged, port = DEFAULT_PORT }) {
  if (backendProcess) {
    return { port, url: getBackendUrl(port), process: backendProcess };
  }

  recentOutput = '';

  if (isPackaged) {
    const backendPath = getPackagedBackendPath();
    if (!fs.existsSync(backendPath)) {
      throw new Error(`Packaged backend sidecar not found: ${backendPath}`);
    }

    backendProcess = spawn(backendPath, [], {
      cwd: path.dirname(backendPath),
      env: {
        ...process.env,
        PORT: String(port),
        GOOGLE_FORM_TOOL_NO_BROWSER: '1',
        GOOGLE_FORM_TOOL_ELECTRON: '1',
      },
      windowsHide: true,
    });
  } else {
    backendProcess = spawn('python', ['wsgi.py'], {
      cwd: appPath,
      env: {
        ...process.env,
        PORT: String(port),
        GOOGLE_FORM_TOOL_NO_BROWSER: '1',
        GOOGLE_FORM_TOOL_ELECTRON: '1',
      },
      windowsHide: true,
    });
  }

  backendProcess.stdout?.on('data', appendOutput);
  backendProcess.stderr?.on('data', appendOutput);
  backendProcess.once('exit', (code, signal) => {
    appendOutput(`\nBackend exited with code ${code ?? 'null'} signal ${signal ?? 'null'}.`);
    backendProcess = null;
  });
  backendProcess.once('error', (error) => {
    appendOutput(`\nBackend failed to start: ${error.message}`);
    backendProcess = null;
  });

  return { port, url: getBackendUrl(port), process: backendProcess };
}

function getRecentOutput() {
  return recentOutput.trim();
}

function isBackendRunning() {
  return Boolean(backendProcess && !backendProcess.killed);
}

function stopBackend() {
  if (!backendProcess || backendProcess.killed) {
    backendProcess = null;
    return;
  }

  const child = backendProcess;
  backendProcess = null;

  if (process.platform === 'win32') {
    spawn('taskkill', ['/pid', String(child.pid), '/T', '/F'], { windowsHide: true });
  } else {
    child.kill('SIGTERM');
  }
}

module.exports = {
  DEFAULT_PORT,
  getRecentOutput,
  isBackendRunning,
  startBackend,
  stopBackend,
};
