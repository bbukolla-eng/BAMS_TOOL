import {
  app,
  BrowserWindow,
  dialog,
  ipcMain,
  Menu,
  shell,
} from 'electron'
import { autoUpdater } from 'electron-updater'
import Store from 'electron-store'
import { spawn, ChildProcess } from 'child_process'
import * as path from 'path'
import * as fs from 'fs'

const store = new Store()

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

const BACKEND_PORT = 8765
const FRONTEND_DIST = app.isPackaged
  ? path.join(process.resourcesPath, 'frontend', 'dist')
  : path.join(__dirname, '../../frontend/dist')
const IS_DEV = process.env.NODE_ENV === 'development'

// ── Backend lifecycle ──────────────────────────────────────────────────────

function startBackend(): void {
  const backendDir = app.isPackaged
    ? path.join(process.resourcesPath, 'backend')
    : path.join(__dirname, '../../backend')

  const pythonBin = app.isPackaged
    ? path.join(backendDir, '.venv', 'bin', 'python')
    : 'python'

  const env = {
    ...process.env,
    PORT: String(BACKEND_PORT),
    DATABASE_URL: `sqlite+aiosqlite:///${path.join(app.getPath('userData'), 'bams.db')}`,
    STORAGE_BACKEND: 'local',
    LOCAL_STORAGE_PATH: path.join(app.getPath('userData'), 'storage'),
    ML_MODELS_PATH: path.join(app.getPath('userData'), 'ml_models'),
  }

  backendProcess = spawn(
    pythonBin,
    ['-m', 'uvicorn', 'api.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)],
    { cwd: backendDir, env, stdio: 'pipe' }
  )

  backendProcess.stdout?.on('data', (d) => console.log('[backend]', d.toString().trim()))
  backendProcess.stderr?.on('data', (d) => console.error('[backend]', d.toString().trim()))

  backendProcess.on('exit', (code) => {
    console.log(`[backend] exited with code ${code}`)
    backendProcess = null
  })
}

function stopBackend(): void {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
}

// ── Window ─────────────────────────────────────────────────────────────────

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 700,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '../assets/icon.png'),
  })

  if (IS_DEV) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(FRONTEND_DIST, 'index.html'))
  }

  mainWindow.on('closed', () => { mainWindow = null })

  buildMenu()
}

// ── Menu ───────────────────────────────────────────────────────────────────

function buildMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Open Drawing…',
          accelerator: 'CmdOrCtrl+O',
          click: async () => {
            const { filePaths } = await dialog.showOpenDialog({
              properties: ['openFile', 'multiSelections'],
              filters: [
                { name: 'MEP Drawings', extensions: ['pdf', 'dwg', 'dxf', 'png', 'jpg', 'tif', 'tiff'] },
                { name: 'All Files', extensions: ['*'] },
              ],
            })
            if (filePaths.length) {
              mainWindow?.webContents.send('open-files', filePaths)
            }
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'BAMS AI Documentation',
          click: () => shell.openExternal('https://docs.bamsai.com'),
        },
        { type: 'separator' },
        {
          label: 'Check for Updates',
          click: () => autoUpdater.checkForUpdatesAndNotify(),
        },
      ],
    },
  ]

  if (process.platform === 'darwin') {
    template.unshift({
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    })
  }

  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

// ── IPC handlers ───────────────────────────────────────────────────────────

ipcMain.handle('get-backend-url', () => `http://127.0.0.1:${BACKEND_PORT}`)

ipcMain.handle('get-app-version', () => app.getVersion())

ipcMain.handle('get-user-data-path', () => app.getPath('userData'))

ipcMain.handle('store-get', (_evt, key: string) => store.get(key))

ipcMain.handle('store-set', (_evt, key: string, value: unknown) => store.set(key, value))

ipcMain.handle('open-file-dialog', async (_evt, options: Electron.OpenDialogOptions) => {
  return dialog.showOpenDialog(options)
})

ipcMain.handle('save-file-dialog', async (_evt, options: Electron.SaveDialogOptions) => {
  return dialog.showSaveDialog(options)
})

ipcMain.handle('write-file', async (_evt, filePath: string, data: string) => {
  fs.writeFileSync(filePath, Buffer.from(data, 'base64'))
  return true
})

// ── App lifecycle ──────────────────────────────────────────────────────────

app.whenReady().then(() => {
  startBackend()
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopBackend()
    app.quit()
  }
})

app.on('before-quit', stopBackend)
