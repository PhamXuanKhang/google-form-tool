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

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function shouldOpenExternally(url) {
  try {
    const parsed = new URL(url);
    const appOrigin = new URL(backendUrl).origin;
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && parsed.origin !== appOrigin;
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
