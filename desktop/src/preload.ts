import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('bamsElectron', {
  getBackendUrl: (): Promise<string> =>
    ipcRenderer.invoke('get-backend-url'),

  getAppVersion: (): Promise<string> =>
    ipcRenderer.invoke('get-app-version'),

  getUserDataPath: (): Promise<string> =>
    ipcRenderer.invoke('get-user-data-path'),

  storeGet: (key: string): Promise<unknown> =>
    ipcRenderer.invoke('store-get', key),

  storeSet: (key: string, value: unknown): Promise<void> =>
    ipcRenderer.invoke('store-set', key, value),

  openFileDialog: (options: Electron.OpenDialogOptions): Promise<Electron.OpenDialogReturnValue> =>
    ipcRenderer.invoke('open-file-dialog', options),

  saveFileDialog: (options: Electron.SaveDialogOptions): Promise<Electron.SaveDialogReturnValue> =>
    ipcRenderer.invoke('save-file-dialog', options),

  writeFile: (filePath: string, base64Data: string): Promise<boolean> =>
    ipcRenderer.invoke('write-file', filePath, base64Data),

  onOpenFiles: (callback: (paths: string[]) => void) => {
    ipcRenderer.on('open-files', (_event, paths) => callback(paths))
    return () => ipcRenderer.removeAllListeners('open-files')
  },
})
