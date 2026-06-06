"""
shaz/utils/helpers.py
Funções utilitárias para o Shaz AI.
"""
from __future__ import annotations

import asyncio
import json
import os
import platform
import re
import socket
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_system_info() -> Dict[str, Any]:
    """Obtém informações do sistema."""
    try:
        import psutil

        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "memory_percent": psutil.virtual_memory().percent,
            "python_version": sys.version,
            "current_time": datetime.now().isoformat(),
        }
    except ImportError:
        return {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": socket.gethostname(),
            "python_version": sys.version,
            "current_time": datetime.now().isoformat(),
        }


def sanitize_text(text: str) -> str:
    """Remove caracteres especiais que podem causar problemas."""
    # Remove caracteres de controle
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Remove múltiplos espaços
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def truncate_text(text: str, max_length: int = 100) -> str:
    """Trunca texto para um tamanho máximo."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def extract_keywords(text: str) -> List[str]:
    """Extrai palavras-chave de um texto."""
    # Remove pontuação e converte para minúsculo
    clean = re.sub(r'[^\w\s]', ' ', text.lower())
    words = clean.split()
    # Remove palavras muito curtas
    words = [w for w in words if len(w) > 2]
    return words


def format_timestamp(ts: Optional[str] = None) -> str:
    """Formata timestamp para exibição."""
    if ts is None:
        return datetime.now().strftime("%H:%M:%S")
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return str(ts)[:8]


def bytes_to_human(size_bytes: int) -> str:
    """Converte bytes para formato legível."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def is_ffmpeg_available() -> bool:
    """Verifica se FFmpeg está disponível no sistema."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def is_internet_available() -> bool:
    """Verifica se há conexão com a internet."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


def generate_id() -> str:
    """Gera um ID único."""
    return str(uuid.uuid4())


def ensure_dir(path: str) -> Path:
    """Garante que um diretório existe."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(path: str, default: Any = None) -> Any:
    """Carrega um arquivo JSON."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: str, data: Any) -> None:
    """Salva dados em um arquivo JSON."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def split_sentences(text: str, max_length: int = 500) -> List[str]:
    """
    Divide texto em sentenças para processamento de TTS.
    Respeita pontuação para quebras naturais.
    """
    if len(text) <= max_length:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= max_length:
            current += " " + sentence if current else sentence
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


def get_audio_devices() -> List[Dict[str, Any]]:
    """Lista dispositivos de áudio disponíveis."""
    devices = []
    try:
        import sounddevice as sd
        for i, dev in enumerate(sd.query_devices()):
            devices.append({
                "index": i,
                "name": dev["name"],
                "channels_in": dev["max_input_channels"],
                "channels_out": dev["max_output_channels"],
                "sample_rate": dev["default_samplerate"],
            })
    except ImportError:
        devices.append({"name": "sounddevice not available"})
    except Exception:
        devices.append({"name": "Could not query audio devices"})

    return devices


def clear_screen() -> None:
    """Limpa a tela do terminal."""
    os.system('cls' if platform.system() == 'Windows' else 'clear')


def async_run(coro) -> Any:
    """Executa uma coroutine de forma síncrona."""
    try:
        # Tenta detectar se já existe um loop rodando no thread atual
        asyncio.get_running_loop()
        # Se existe, precisamos rodar em uma thread separada com seu próprio loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    except RuntimeError:
        # Nenhum loop rodando, podemos usar asyncio.run diretamente
        return asyncio.run(coro)