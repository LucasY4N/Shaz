/**
 * preload.js — Bridge segura entre o processo main (Node.js) e o renderer (HTML)
 *
 * contextIsolation = true → este arquivo roda em contexto isolado.
 * Expõe apenas o que for necessário via contextBridge.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /** Versão do app */
  getVersion: () => ipcRenderer.invoke('get-version'),

  /** Status do processo Python */
  getPythonStatus: () => ipcRenderer.invoke('get-python-status'),

  /** Indica que estamos rodando dentro do Electron */
  isElectron: true,
});
