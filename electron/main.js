/**
 * main.js — Processo principal Electron para Shaz OS
 *
 * Responsabilidades:
 *  - Criar a janela nativa (BrowserWindow)
 *  - Carregar o shaz-terminal.html
 *  - Iniciar o servidor Python (run_server.py) como processo filho
 *  - Matar o Python quando a janela fechar
 */

const { app, BrowserWindow, shell, ipcMain, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// ── Config ────────────────────────────────────────────────────────────────────

// Em dev (npm start), o HTML está no diretório pai; em produção, extraFiles copia para o resourcesPath
const isDev = !app.isPackaged;

const HTML_PATH = fs.existsSync(path.join(__dirname, 'shaz-terminal.html'))
  ? path.join(__dirname, 'shaz-terminal.html')
  : path.join(__dirname, '..', 'shaz-terminal.html');

// Diretório raiz do projeto Python
const PYTHON_ROOT = isDev
  ? path.join(__dirname, '..')
  : path.join(process.resourcesPath);

// ── Estado ────────────────────────────────────────────────────────────────────

let mainWindow = null;
let pythonProcess = null;

// ── Iniciar backend Python ────────────────────────────────────────────────────

function startPythonBackend() {
  const serverScript = path.join(PYTHON_ROOT, 'run_server.py');

  if (!fs.existsSync(serverScript)) {
    console.warn('[Shaz] run_server.py não encontrado. Backend não será iniciado automaticamente.');
    return;
  }

  console.log('[Shaz] Iniciando backend Python:', serverScript);

  // Tenta usar python3 primeiro, depois python
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  pythonProcess = spawn(pythonCmd, [serverScript], {
    cwd: PYTHON_ROOT,
    stdio: ['ignore', 'pipe', 'pipe'],
    detached: false,
  });

  pythonProcess.stdout.on('data', (data) => {
    process.stdout.write(`[Python] ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    process.stderr.write(`[Python ERR] ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Shaz] Backend Python encerrado com código: ${code}`);
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    console.error('[Shaz] Erro ao iniciar Python:', err.message);
    pythonProcess = null;
  });
}

function stopPythonBackend() {
  if (!pythonProcess) return;
  console.log('[Shaz] Encerrando backend Python...');
  if (process.platform === 'win32') {
    spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
  } else {
    pythonProcess.kill('SIGTERM');
  }
  pythonProcess = null;
}

// ── Janela principal ──────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1100,
    minHeight: 680,
    title: 'Shaz OS — NEXUS v3.0',
    backgroundColor: '#080c14',
    // Sem frame nativo: a interface HTML já tem visual próprio
    frame: true,
    // icon (converta para .ico usando sharp ou online antes do build)
    // icon: path.join(__dirname, 'assets', 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      // Permite carregar file:// e conectar a localhost:8765 sem bloqueio CORS
      webSecurity: false,
    },
    show: false, // aguarda 'ready-to-show' para exibir sem flash branco
  });

  // Remove a barra de menu padrão do Electron
  Menu.setApplicationMenu(null);

  // Carrega o HTML
  mainWindow.loadFile(HTML_PATH);

  // Exibe só depois de renderizado (sem flash branco)
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (isDev) mainWindow.webContents.openDevTools({ mode: 'detach' });
  });

  // Abre links externos no navegador padrão
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ── Ciclo de vida do app ──────────────────────────────────────────────────────

app.whenReady().then(() => {
  // 1. Inicia o servidor Python
  startPythonBackend();

  // 2. Aguarda um momento para o servidor iniciar antes de abrir a janela
  setTimeout(createWindow, 800);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  stopPythonBackend();
});

// ── IPC Handlers (comunicação segura HTML → main) ─────────────────────────────

// Exemplo: renderer pode chamar window.electronAPI.getVersion()
ipcMain.handle('get-version', () => app.getVersion());

ipcMain.handle('get-python-status', () => ({
  running: pythonProcess !== null,
  pid: pythonProcess?.pid ?? null,
}));
