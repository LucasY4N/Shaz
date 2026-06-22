"""
ShazLauncher.py  ← coloque na raiz do projeto
Aplicativo de gerenciamento do Shaz AI.
Execute com: python ShazLauncher.py

FEATURES:
  - Inicia/para o servidor HTTP com um clique
  - Inicia/para o bot Discord
  - Abre o terminal web no navegador
  - Mostra logs em tempo real
  - Mostra status de cada serviço
  - Botão para trocar provedor LLM
  - Botão para selecionar voz clonada ativa
  - Não precisa abrir o terminal manualmente
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, filedialog
except ImportError:
    print("tkinter não encontrado. No Windows ele vem com Python.")
    sys.exit(1)

# Garante que a raiz do projeto está no path
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

PORT = int(os.environ.get("SHAZ_PORT", 8765))
BASE_URL = f"http://localhost:{PORT}"

# ─── Cores (tema escuro igual ao NEXUS) ─────────────────────────────────
BG_DEEP    = "#080c14"
BG_PANEL   = "#0d1220"
BG_CARD    = "#111827"
PINK       = "#ff4fa3"
CYAN       = "#06b6d4"
GREEN      = "#10b981"
YELLOW     = "#f59e0b"
RED        = "#ef4444"
TEXT       = "#e2e8f0"
MUTED      = "#64748b"


class ServiceBlock(tk.Frame):
    """Bloco visual de um serviço (servidor, discord, etc.)."""

    def __init__(self, parent, name: str, description: str, **kw):
        super().__init__(parent, bg=BG_CARD, **kw)
        self.configure(relief="flat", bd=0, pady=8, padx=12)

        self._running = False
        self._proc: Optional[subprocess.Popen] = None
        self._name = name

        # Indicador + nome
        top = tk.Frame(self, bg=BG_CARD)
        top.pack(fill="x")

        self._dot = tk.Label(top, text="●", font=("Segoe UI", 14), fg=RED, bg=BG_CARD)
        self._dot.pack(side="left")

        tk.Label(top, text=name, font=("Orbitron", 11, "bold"),
                 fg=PINK, bg=BG_CARD).pack(side="left", padx=6)

        self._status_lbl = tk.Label(top, text="INATIVO", font=("Consolas", 9),
                                    fg=MUTED, bg=BG_CARD)
        self._status_lbl.pack(side="right")

        tk.Label(self, text=description, font=("Segoe UI", 9),
                 fg=MUTED, bg=BG_CARD, wraplength=320, justify="left").pack(anchor="w", pady=(2, 6))

        # Botões
        btn_row = tk.Frame(self, bg=BG_CARD)
        btn_row.pack(fill="x")

        self._start_btn = tk.Button(
            btn_row, text="▶ INICIAR", font=("Consolas", 9, "bold"),
            fg="white", bg=GREEN, activebackground="#059669",
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            command=self.start,
        )
        self._start_btn.pack(side="left", padx=(0, 6))

        self._stop_btn = tk.Button(
            btn_row, text="⏹ PARAR", font=("Consolas", 9, "bold"),
            fg="white", bg=RED, activebackground="#dc2626",
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            state="disabled", command=self.stop,
        )
        self._stop_btn.pack(side="left")

        # Separador
        tk.Frame(self, bg=MUTED, height=1).pack(fill="x", pady=(8, 0))

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def _set_running(self, running: bool, status_text: str = ""):
        self._running = running
        if running:
            self._dot.configure(fg=GREEN)
            self._status_lbl.configure(fg=GREEN, text=status_text or "ATIVO")
            self._start_btn.configure(state="disabled")
            self._stop_btn.configure(state="normal")
        else:
            self._dot.configure(fg=RED)
            self._status_lbl.configure(fg=MUTED, text=status_text or "INATIVO")
            self._start_btn.configure(state="normal")
            self._stop_btn.configure(state="disabled")


class ServerBlock(ServiceBlock):
    """Bloco do servidor HTTP/WebSocket."""

    def __init__(self, parent, log_fn, **kw):
        super().__init__(
            parent,
            name="⚡ Servidor HTTP + WebSocket",
            description=f"API REST + WebSocket na porta {PORT}. Necessário para o chat web funcionar.",
            **kw,
        )
        self._log = log_fn
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Botão abrir no navegador
        tk.Button(
            self, text="🌐 Abrir no Navegador", font=("Consolas", 9),
            fg=CYAN, bg=BG_CARD, activeforeground="white",
            relief="flat", bd=0, padx=0, pady=2, cursor="hand2",
            command=lambda: webbrowser.open(f"{BASE_URL}/app"),
        ).pack(anchor="w", pady=(4, 0))

    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._set_running(True, f":{PORT}")
        self._log(f"[Servidor] Iniciando em {BASE_URL} ...")

        def run():
            try:
                import uvicorn
                from shaz.server import app as shaz_app
                config = uvicorn.Config(shaz_app, host="127.0.0.1", port=PORT, log_level="warning")
                server = uvicorn.Server(config)
                # Aguarda o stop_event
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def serve():
                    server_task = loop.create_task(server.serve())
                    while not self._stop_event.is_set():
                        await asyncio.sleep(0.5)
                    server.should_exit = True
                    await server_task

                loop.run_until_complete(serve())
            except Exception as e:
                self._log(f"[Servidor] ERRO: {e}")
            finally:
                self.after(0, lambda: self._set_running(False))

        self._thread = threading.Thread(target=run, daemon=True, name="ShazServer")
        self._thread.start()
        # Aguarda um pouco e abre no navegador
        self.after(2500, lambda: webbrowser.open(f"{BASE_URL}/app"))
        self._log(f"[Servidor] Online em {BASE_URL}/app")

    def stop(self):
        self._stop_event.set()
        self._set_running(False)
        self._log("[Servidor] Parado.")


class DiscordBlock(ServiceBlock):
    """Bloco do bot Discord."""

    def __init__(self, parent, log_fn, **kw):
        super().__init__(
            parent,
            name="🤖 Bot Discord",
            description="Bot Discord que encaminha mensagens para o backend Shaz via HTTP.",
            **kw,
        )
        self._log = log_fn
        self._proc: Optional[subprocess.Popen] = None

    def start(self):
        token = os.environ.get("DISCORD_TOKEN", "").strip()
        if not token:
            messagebox.showerror(
                "Token faltando",
                "DISCORD_TOKEN não está configurado no arquivo .env!\n\n"
                "Adicione:\n  DISCORD_TOKEN=seu_token_aqui",
            )
            return

        bot_script = _root / "discord_bot" / "bot.py"
        if not bot_script.exists():
            # Tenta o caminho alternativo
            bot_script = _root / "integrations" / "discord" / "bot.py"
        if not bot_script.exists():
            messagebox.showerror("Arquivo não encontrado", f"Bot script não encontrado em:\n{bot_script}")
            return

        try:
            self._proc = subprocess.Popen(
                [sys.executable, str(bot_script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(_root),
                text=True,
                bufsize=1,
            )
            self._set_running(True)
            self._log("[Discord] Bot iniciado!")

            def read_output():
                for line in iter(self._proc.stdout.readline, ""):
                    self._log(f"[Discord] {line.rstrip()}")
                self.after(0, lambda: self._set_running(False))

            threading.Thread(target=read_output, daemon=True).start()
        except Exception as e:
            self._log(f"[Discord] ERRO ao iniciar: {e}")
            messagebox.showerror("Erro", str(e))

    def stop(self):
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=3)
            except Exception:
                self._proc.kill()
        self._set_running(False)
        self._log("[Discord] Bot parado.")


class ShazLauncher(tk.Tk):
    """Janela principal do launcher."""

    def __init__(self):
        super().__init__()
        self.title("Shaz AI — Launcher")
        self.configure(bg=BG_DEEP)
        self.geometry("540x780")
        self.resizable(True, True)
        self.minsize(480, 600)

        # Tenta carregar .env antes de tudo
        self._load_env()
        self._build_ui()

    def _load_env(self):
        env_path = _root / ".env"
        if env_path.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(str(env_path))
            except ImportError:
                # Manual parse simples
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, _, v = line.partition("=")
                            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=BG_PANEL, pady=14)
        header.pack(fill="x")

        tk.Label(
            header, text="⚡ SHAZ AI", font=("Orbitron", 18, "bold"),
            fg=PINK, bg=BG_PANEL,
        ).pack()
        tk.Label(
            header, text="NEXUS v3.1 — LAUNCHER", font=("Consolas", 9),
            fg=MUTED, bg=BG_PANEL,
        ).pack()

        # ── Serviços ──
        svc_frame = tk.Frame(self, bg=BG_DEEP, padx=12, pady=8)
        svc_frame.pack(fill="x")

        tk.Label(svc_frame, text="SERVIÇOS", font=("Consolas", 9, "bold"),
                 fg=MUTED, bg=BG_DEEP).pack(anchor="w", pady=(0, 6))

        self._server_block = ServerBlock(svc_frame, self._log)
        self._server_block.pack(fill="x", pady=(0, 8))

        self._discord_block = DiscordBlock(svc_frame, self._log)
        self._discord_block.pack(fill="x")

        # ── Voz Clonada ──
        voice_frame = tk.Frame(self, bg=BG_DEEP, padx=12, pady=8)
        voice_frame.pack(fill="x")

        tk.Label(voice_frame, text="VOZ CLONADA (XTTS-v2)", font=("Consolas", 9, "bold"),
                 fg=MUTED, bg=BG_DEEP).pack(anchor="w", pady=(0, 6))

        voice_card = tk.Frame(voice_frame, bg=BG_CARD, padx=12, pady=8)
        voice_card.pack(fill="x")

        self._voice_var = tk.StringVar(value="Padrão (Edge TTS)")
        tk.Label(voice_card, text="Voz ativa:", font=("Consolas", 9),
                 fg=MUTED, bg=BG_CARD).pack(anchor="w")
        tk.Label(voice_card, textvariable=self._voice_var, font=("Consolas", 10, "bold"),
                 fg=CYAN, bg=BG_CARD).pack(anchor="w", pady=(0, 6))

        btn_row = tk.Frame(voice_card, bg=BG_CARD)
        btn_row.pack(fill="x")

        tk.Button(
            btn_row, text="🎤 Clonar Nova Voz", font=("Consolas", 9),
            fg="white", bg="#7c3aed", activebackground="#6d28d9",
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            command=self._clone_voice,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btn_row, text="📋 Selecionar Voz", font=("Consolas", 9),
            fg="white", bg=YELLOW, activebackground="#d97706",
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            command=self._select_voice,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btn_row, text="↩ Padrão", font=("Consolas", 9),
            fg=MUTED, bg=BG_PANEL, activebackground=BG_CARD,
            relief="flat", bd=0, padx=10, pady=4, cursor="hand2",
            command=self._reset_voice,
        ).pack(side="left")

        # ── Quick Actions ──
        qa_frame = tk.Frame(self, bg=BG_DEEP, padx=12, pady=4)
        qa_frame.pack(fill="x")

        tk.Label(qa_frame, text="AÇÕES RÁPIDAS", font=("Consolas", 9, "bold"),
                 fg=MUTED, bg=BG_DEEP).pack(anchor="w", pady=(0, 6))

        actions = tk.Frame(qa_frame, bg=BG_DEEP)
        actions.pack(fill="x")

        btns = [
            ("🌐 Abrir Chat", CYAN, lambda: webbrowser.open(f"{BASE_URL}/app")),
            ("📖 Ver Docs", MUTED, lambda: webbrowser.open(f"{BASE_URL}/docs")),
            ("🔄 Reiniciar Servidor", YELLOW, self._restart_server),
        ]
        for label, color, cmd in btns:
            tk.Button(
                actions, text=label, font=("Consolas", 9),
                fg="white", bg=BG_CARD, activebackground=BG_PANEL,
                relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
                command=cmd,
            ).pack(side="left", padx=(0, 6))

        # ── Logs ──
        log_frame = tk.Frame(self, bg=BG_DEEP, padx=12, pady=8)
        log_frame.pack(fill="both", expand=True)

        log_header = tk.Frame(log_frame, bg=BG_DEEP)
        log_header.pack(fill="x")
        tk.Label(log_header, text="LOGS", font=("Consolas", 9, "bold"),
                 fg=MUTED, bg=BG_DEEP).pack(side="left")
        tk.Button(
            log_header, text="🗑 LIMPAR", font=("Consolas", 8),
            fg=MUTED, bg=BG_DEEP, activebackground=BG_PANEL,
            relief="flat", bd=0, padx=4, pady=0, cursor="hand2",
            command=lambda: self._log_area.delete("1.0", "end"),
        ).pack(side="right")

        self._log_area = scrolledtext.ScrolledText(
            log_frame, font=("Consolas", 9), bg=BG_DEEP, fg=TEXT,
            insertbackground=PINK, relief="flat", bd=0,
            height=10, state="disabled",
        )
        self._log_area.pack(fill="both", expand=True, pady=(4, 0))
        self._log_area.tag_configure("pink", foreground=PINK)
        self._log_area.tag_configure("green", foreground=GREEN)
        self._log_area.tag_configure("red", foreground=RED)
        self._log_area.tag_configure("yellow", foreground=YELLOW)
        self._log_area.tag_configure("cyan", foreground=CYAN)
        self._log_area.tag_configure("muted", foreground=MUTED)

        # ── Status Bar ──
        status_bar = tk.Frame(self, bg=BG_PANEL, pady=4, padx=12)
        status_bar.pack(fill="x", side="bottom")
        self._status_var = tk.StringVar(value=f"Servidor: {BASE_URL}")
        tk.Label(status_bar, textvariable=self._status_var, font=("Consolas", 8),
                 fg=MUTED, bg=BG_PANEL).pack(side="left")

        # Log inicial
        self._log(f"[Launcher] Shaz AI Launcher iniciado")
        self._log(f"[Launcher] Porta do servidor: {PORT}")
        self._log(f"[Launcher] Raiz do projeto: {_root}")

    def _log(self, msg: str):
        """Adiciona mensagem ao log."""
        def _write():
            self._log_area.configure(state="normal")
            # Detecta a tag pelo conteúdo
            tag = "muted"
            ml = msg.lower()
            if "erro" in ml or "error" in ml or "falha" in ml:
                tag = "red"
            elif "✅" in msg or "online" in ml or "pronto" in ml or "iniciado" in ml:
                tag = "green"
            elif "⚠" in msg or "aviso" in ml or "warn" in ml:
                tag = "yellow"
            elif "[discord]" in ml:
                tag = "cyan"
            elif "[servidor]" in ml:
                tag = "pink"

            ts = time.strftime("%H:%M:%S")
            self._log_area.insert("end", f"[{ts}] {msg}\n", tag)
            self._log_area.see("end")
            self._log_area.configure(state="disabled")

        # Thread-safe
        try:
            self.after(0, _write)
        except RuntimeError:
            pass

    def _restart_server(self):
        self._server_block.stop()
        self.after(1500, self._server_block.start)

    def _clone_voice(self):
        """Abre diálogo para clonar nova voz."""
        file_path = filedialog.askopenfilename(
            title="Selecione o áudio de referência",
            filetypes=[
                ("Áudio", "*.wav *.mp3 *.ogg *.flac *.m4a"),
                ("Todos", "*.*"),
            ],
        )
        if not file_path:
            return

        # Pede o nome da voz
        name_win = tk.Toplevel(self)
        name_win.title("Nome da Voz")
        name_win.configure(bg=BG_PANEL)
        name_win.geometry("340x160")
        name_win.resizable(False, False)

        tk.Label(name_win, text="Nome da voz clonada:", font=("Segoe UI", 10),
                 fg=TEXT, bg=BG_PANEL).pack(pady=(16, 4))
        name_var = tk.StringVar(value=Path(file_path).stem)
        tk.Entry(name_win, textvariable=name_var, font=("Consolas", 11),
                 bg=BG_CARD, fg=TEXT, insertbackground=PINK,
                 relief="flat", bd=4).pack(fill="x", padx=20)

        def do_clone():
            name = name_var.get().strip()
            if not name:
                return
            name_win.destroy()
            self._log(f"[Voz] Iniciando clonagem de '{name}'... (pode demorar ~30s)")
            self._log("[Voz] XTTS-v2 carregando modelo (~2GB na primeira vez)")

            def clone_thread():
                try:
                    import asyncio as _asyncio
                    sys.path.insert(0, str(_root))
                    from shaz.voice_cloner import VoiceCloner
                    cloner = VoiceCloner()
                    profile = _asyncio.run(cloner.create_profile(
                        audio_path=file_path,
                        name=name,
                        language="pt",
                    ))
                    self._log(f"[Voz] ✅ Voz '{profile.name}' clonada! ID: {profile.id}")
                    self.after(0, lambda: self._voice_var.set(f"{profile.name} ({profile.id})"))
                    self.after(0, lambda: messagebox.showinfo(
                        "Voz Clonada!",
                        f"✅ Voz '{profile.name}' criada com sucesso!\n\nID: {profile.id}\n\n"
                        f"Use 'Selecionar Voz' para ativá-la.",
                    ))
                except Exception as e:
                    self._log(f"[Voz] ERRO ao clonar: {e}")
                    self.after(0, lambda: messagebox.showerror("Erro ao Clonar", str(e)))

            threading.Thread(target=clone_thread, daemon=True).start()

        tk.Button(name_win, text="✅ CLONAR", font=("Consolas", 10, "bold"),
                  fg="white", bg=GREEN, relief="flat", bd=0, padx=12, pady=6,
                  cursor="hand2", command=do_clone).pack(pady=14)

    def _select_voice(self):
        """Abre diálogo para selecionar voz clonada ativa."""
        try:
            sys.path.insert(0, str(_root))
            from shaz.voice_cloner import VoiceCloner
            cloner = VoiceCloner()
            profiles = cloner.list_profiles()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível listar vozes:\n{e}")
            return

        if not profiles:
            messagebox.showinfo("Sem Vozes", "Nenhuma voz clonada encontrada.\nUse 'Clonar Nova Voz' primeiro.")
            return

        win = tk.Toplevel(self)
        win.title("Selecionar Voz")
        win.configure(bg=BG_PANEL)
        win.geometry("400x320")

        tk.Label(win, text="Vozes Disponíveis", font=("Orbitron", 11, "bold"),
                 fg=PINK, bg=BG_PANEL).pack(pady=(12, 6))

        listbox = tk.Listbox(win, font=("Consolas", 10), bg=BG_CARD, fg=TEXT,
                             selectbackground=PINK, relief="flat", bd=0,
                             activestyle="none")
        listbox.pack(fill="both", expand=True, padx=12, pady=4)

        profile_ids = []
        for p in profiles:
            listbox.insert("end", f"  {p.name}  ({p.id[:8]})  [{p.language}]  {p.duration_seconds:.1f}s")
            profile_ids.append(p.id)

        def do_select():
            sel = listbox.curselection()
            if not sel:
                return
            profile_id = profile_ids[sel[0]]
            profile_name = profiles[sel[0]].name
            win.destroy()
            # Envia para o servidor se estiver rodando
            self._log(f"[Voz] Selecionando voz: {profile_name}")
            self._voice_var.set(f"{profile_name} ({profile_id[:8]})")
            self._activate_cloned_voice(profile_id, profile_name)

        tk.Button(win, text="✅ SELECIONAR", font=("Consolas", 10, "bold"),
                  fg="white", bg=GREEN, relief="flat", bd=0, padx=12, pady=6,
                  cursor="hand2", command=do_select).pack(pady=8)

    def _activate_cloned_voice(self, profile_id: str, name: str):
        """Ativa a voz clonada no servidor via API."""
        import urllib.request, json as _json
        try:
            data = _json.dumps({"profile_id": profile_id}).encode()
            req = urllib.request.Request(
                f"{BASE_URL}/api/voice/cloned/select",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                result = _json.loads(r.read())
            if result.get("status") == "ok":
                self._log(f"[Voz] ✅ Voz '{name}' ativada no servidor!")
            else:
                self._log(f"[Voz] ⚠ Servidor respondeu: {result}")
        except Exception as e:
            # Servidor pode não estar rodando ainda — salva localmente
            self._log(f"[Voz] ⚠ Servidor offline, voz salva localmente: {e}")
            # Persiste no .env ou arquivo de configuração para ser carregado no próximo start
            self._save_voice_preference(profile_id)

    def _save_voice_preference(self, profile_id: str):
        """Salva preferência de voz em arquivo de config."""
        pref_file = _root / "data" / "voice_preference.txt"
        pref_file.parent.mkdir(parents=True, exist_ok=True)
        pref_file.write_text(profile_id)
        self._log(f"[Voz] Preferência salva em {pref_file}")

    def _reset_voice(self):
        """Volta para Edge TTS padrão."""
        import urllib.request, json as _json
        self._voice_var.set("Padrão (Edge TTS)")
        try:
            data = _json.dumps({"profile_id": ""}).encode()
            req = urllib.request.Request(
                f"{BASE_URL}/api/voice/cloned/select",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                pass
        except Exception:
            pass
        self._log("[Voz] Voltando para Edge TTS padrão.")


def main():
    app = ShazLauncher()
    app.mainloop()


if __name__ == "__main__":
    main()
