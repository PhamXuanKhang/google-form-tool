const { app, BrowserWindow, dialog, shell } = require('electron');
const fs = require('node:fs');
const path = require('node:path');

const {
  DEFAULT_PORT,
  getRecentOutput,
  isBackendRunning,
  startBackend,
  stopBackend,
} = require('./backendProcess');

const READINESS_TIMEOUT_MS = 30000;
const READINESS_INTERVAL_MS = 500;
const ALLOWED_EXTERNAL_HOSTS = new Set([
  'github.com',
  'www.linkedin.com',
  'www.google.com',
  'docs.google.com',
]);

let mainWindow = null;
let backendUrl = `http://127.0.0.1:${DEFAULT_PORT}`;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForBackendReady(url) {
  const healthUrl = `${url}/healthz`;
  const startedAt = Date.now();

  while (Date.now() - startedAt < READINESS_TIMEOUT_MS) {
    if (!isBackendRunning()) {
      throw new Error(`Backend exited before it became ready. ${getRecentOutput()}`.trim());
    }

    try {
      const response = await fetch(healthUrl);
      if (response.ok) {
        return;
      }
    } catch (error) {
      // Retry until timeout.
    }

    await sleep(READINESS_INTERVAL_MS);
  }

  throw new Error(`Backend did not become ready at ${healthUrl}. ${getRecentOutput()}`.trim());
}

function getIconPath() {
  const iconPath = path.join(app.getAppPath(), 'app', 'static', 'images', 'app_icon.ico');
  return fs.existsSync(iconPath) ? iconPath : undefined;
}

function createWindow() {
  const options = {
    title: 'Google Form Automation Tool',
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  };

  const icon = getIconPath();
  if (icon) {
    options.icon = icon;
  }

  mainWindow = new BrowserWindow(options);

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (shouldOpenExternally(url)) {
      shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });

  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (shouldOpenExternally(url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  // Closing the app stops any run in progress (the backend is stopped with
  // it), so ask first when something is still sending.
  let closeConfirmed = false;
  mainWindow.on('close', async (event) => {
    if (closeConfirmed) {
      return;
    }
    event.preventDefault();
    const running = await countRunningSubmissions();
    if (running > 0) {
      const { response } = await dialog.showMessageBox(mainWindow, {
        type: 'warning',
        buttons: ['Keep running', 'Close anyway'],
        defaultId: 0,
        cancelId: 0,
        title: 'A run is in progress',
        message: running === 1 ? 'A form run is still in progress.' : `${running} form runs are still in progress.`,
        detail: 'Closing the app stops sending. Scheduled runs can be resumed from their report the next time you open the app.',
      });
      if (response === 0) {
        return;
      }
    }
    closeConfirmed = true;
    mainWindow?.close();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

async function countRunningSubmissions() {
  try {
    const response = await fetch(`${backendUrl}/submission_status`);
    if (!response.ok) {
      return 0;
    }
    const data = await response.json();
    return Object.values(data.active_submissions || {}).filter((status) => status && status.running).length;
  } catch (error) {
    return 0;
  }
}

function shouldOpenExternally(url) {
  try {
    const parsed = new URL(url);
    const appOrigin = new URL(backendUrl).origin;

    if (parsed.origin === appOrigin) {
      return false;
    }
    if (parsed.protocol === 'mailto:') {
      return true;
    }
    if (parsed.protocol !== 'https:') {
      return false;
    }
    return ALLOWED_EXTERNAL_HOSTS.has(parsed.hostname);
  } catch (error) {
    return false;
  }
}

async function showStartupError(error) {
  const details = error?.message || String(error);
  await dialog.showMessageBox({
    type: 'error',
    title: 'Google Form Tool — Startup Error',
    message: 'The local backend could not start.',
    detail: details,
  });
}

async function launch() {
  createWindow();

  try {
    const backend = startBackend({
      appPath: app.getAppPath(),
      isPackaged: app.isPackaged,
      port: Number(process.env.PORT || DEFAULT_PORT),
    });
    backendUrl = backend.url;

    await waitForBackendReady(backendUrl);
    await mainWindow.loadURL(backendUrl);
  } catch (error) {
    await showStartupError(error);
    app.quit();
  }
}

app.whenReady().then(launch);

app.on('before-quit', () => {
  stopBackend();
});

app.on('window-all-closed', () => {
  stopBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    launch();
  }
});
