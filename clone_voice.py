#!/usr/bin/env python3
"""
clone_voice.py
Script de linha de comando para clonar vozes e gerar mensagens.

Uso:
    # Clonar uma voz (cria um perfil)
    python clone_voice.py clonar --audio minha_voz.mp3 --nome "Minha Voz" --lang pt

    # Listar perfis salvos
    python clone_voice.py listar

    # Gerar mensagem com voz clonada
    python clone_voice.py gerar --perfil <ID> --texto "Olá, isso é um teste!" --saida saida.wav

    # Gerar mensagem de forma interativa (digita o texto no terminal)
    python clone_voice.py gerar --perfil <ID> --saida saida.wav

    # Clonar E gerar em um único comando
    python clone_voice.py clonar-gerar --audio minha_voz.mp3 --texto "Olá mundo!" --saida saida.wav
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent))


def _print_ok(msg: str) -> None:
    print(f"\033[92m✓ {msg}\033[0m")

def _print_err(msg: str) -> None:
    print(f"\033[91m✗ {msg}\033[0m")

def _print_info(msg: str) -> None:
    print(f"\033[94mℹ {msg}\033[0m")

def _print_warn(msg: str) -> None:
    print(f"\033[93m⚠ {msg}\033[0m")


# ─── Comando: clonar ─────────────────────────────────────────────────────

async def cmd_clonar(audio: str, nome: str, lang: str, descricao: str) -> None:
    """Cria um perfil de voz a partir de um áudio de referência."""
    from shaz.voice.voice_cloner import VoiceCloner

    _print_info(f"Iniciando clonagem de '{nome}' a partir de '{audio}'...")
    _print_info("Isso pode demorar alguns segundos na primeira vez (download do modelo ~2GB).")
    print()

    cloner = VoiceCloner()

    try:
        profile = await cloner.create_profile(
            audio_path=audio,
            name=nome,
            language=lang,
            description=descricao,
        )
        print()
        _print_ok(f"Perfil criado com sucesso!")
        print(f"  Nome:     {profile.name}")
        print(f"  ID:       {profile.id}")
        print(f"  Idioma:   {profile.language}")
        print(f"  Duração:  {profile.duration_seconds:.1f}s")
        print(f"  Referência: {profile.reference_wav}")
        print()
        _print_info(f"Use este ID para gerar mensagens:")
        print(f"  python clone_voice.py gerar --perfil {profile.id} --texto \"Sua mensagem aqui\" --saida saida.wav")

    except FileNotFoundError as e:
        _print_err(f"Arquivo não encontrado: {e}")
        sys.exit(1)
    except ValueError as e:
        _print_err(f"Áudio inválido: {e}")
        sys.exit(1)
    except RuntimeError as e:
        _print_err(str(e))
        sys.exit(1)


# ─── Comando: listar ─────────────────────────────────────────────────────

def cmd_listar() -> None:
    """Lista todos os perfis de voz salvos."""
    from shaz.voice.voice_cloner import VoiceCloner

    cloner = VoiceCloner()
    profiles = cloner.list_profiles()

    if not profiles:
        _print_warn("Nenhum perfil de voz encontrado.")
        print("Crie um com: python clone_voice.py clonar --audio sua_voz.wav --nome \"Minha Voz\"")
        return

    print(f"\n{'─'*60}")
    print(f"  {'ID':<12} {'Nome':<20} {'Idioma':<8} {'Duração':<10} {'Criado'}")
    print(f"{'─'*60}")
    for p in profiles:
        criado = p.created_at[:10] if p.created_at else "?"
        duracao = f"{p.duration_seconds:.1f}s"
        print(f"  {p.id:<12} {p.name:<20} {p.language:<8} {duracao:<10} {criado}")
    print(f"{'─'*60}\n")
    print(f"  Total: {len(profiles)} perfil(s)\n")


# ─── Comando: gerar ──────────────────────────────────────────────────────

async def cmd_gerar(
    perfil_id: str,
    texto: Optional[str],
    saida: str,
    velocidade: float,
    temperatura: float,
    reproduzir: bool,
) -> None:
    """Gera uma mensagem de áudio usando um perfil de voz clonada."""
    from shaz.voice.voice_cloner import VoiceCloner

    cloner = VoiceCloner()
    profile = cloner.get_profile(perfil_id)

    if not profile:
        _print_err(f"Perfil '{perfil_id}' não encontrado.")
        cmd_listar()
        sys.exit(1)

    _print_info(f"Usando voz: {profile.name} (ID: {profile.id})")

    # Pede o texto se não foi fornecido
    if not texto:
        print("\nDigite o texto que deseja sintetizar (Enter para confirmar):")
        texto = input("  > ").strip()
        if not texto:
            _print_err("Nenhum texto fornecido.")
            sys.exit(1)

    print()
    _print_info(f"Sintetizando: \"{texto[:80]}{'...' if len(texto) > 80 else ''}\"")
    _print_info("Aguarde...")

    try:
        output_path = await cloner.synthesize_and_save(
            text=texto,
            profile_id=perfil_id,
            output_path=saida,
            speed=velocidade,
            temperature=temperatura,
        )

        file_size = Path(output_path).stat().st_size
        _print_ok(f"Áudio gerado: {output_path} ({file_size / 1024:.1f} KB)")

        # Reproduz se solicitado
        if reproduzir:
            _print_info("Reproduzindo áudio...")
            _play_audio(output_path)

    except KeyError as e:
        _print_err(str(e))
        sys.exit(1)
    except RuntimeError as e:
        _print_err(str(e))
        sys.exit(1)


def _play_audio(filepath: str) -> None:
    """Tenta reproduzir o áudio gerado."""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(filepath)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        return
    except Exception:
        pass

    try:
        import sounddevice as sd
        import soundfile as sf
        data, sr = sf.read(filepath)
        sd.play(data, sr)
        sd.wait()
        return
    except Exception:
        pass

    # Fallback: comando do sistema
    import platform, subprocess
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["start", filepath], shell=True, check=False)
        elif system == "Darwin":  # macOS
            subprocess.run(["afplay", filepath], check=False)
        else:  # Linux
            subprocess.run(["aplay", filepath], check=False)
    except Exception:
        _print_warn("Não foi possível reproduzir automaticamente. Abra o arquivo manualmente.")


# ─── Comando: clonar-gerar ───────────────────────────────────────────────

async def cmd_clonar_gerar(
    audio: str,
    nome: str,
    lang: str,
    texto: str,
    saida: str,
    velocidade: float,
    temperatura: float,
    reproduzir: bool,
) -> None:
    """Clona uma voz e gera uma mensagem em um único comando."""
    from shaz.voice.voice_cloner import VoiceCloner

    _print_info("Criando perfil de voz...")
    cloner = VoiceCloner()

    try:
        profile = await cloner.create_profile(
            audio_path=audio,
            name=nome,
            language=lang,
        )
        _print_ok(f"Voz '{nome}' clonada! (ID: {profile.id})")
    except Exception as e:
        _print_err(f"Erro ao clonar: {e}")
        sys.exit(1)

    # Pede o texto se não foi fornecido
    if not texto:
        print("\nDigite o texto que deseja sintetizar:")
        texto = input("  > ").strip()
        if not texto:
            _print_err("Nenhum texto fornecido.")
            sys.exit(1)

    print()
    _print_info("Gerando áudio...")

    try:
        output_path = await cloner.synthesize_and_save(
            text=texto,
            profile_id=profile.id,
            output_path=saida,
            speed=velocidade,
            temperature=temperatura,
        )
        file_size = Path(output_path).stat().st_size
        _print_ok(f"Áudio gerado: {output_path} ({file_size / 1024:.1f} KB)")

        if reproduzir:
            _print_info("Reproduzindo...")
            _play_audio(output_path)

    except Exception as e:
        _print_err(f"Erro ao gerar áudio: {e}")
        sys.exit(1)


# ─── Comando: deletar ────────────────────────────────────────────────────

def cmd_deletar(perfil_id: str) -> None:
    """Remove um perfil de voz."""
    from shaz.voice.voice_cloner import VoiceCloner

    cloner = VoiceCloner()
    profile = cloner.get_profile(perfil_id)

    if not profile:
        _print_err(f"Perfil '{perfil_id}' não encontrado.")
        sys.exit(1)

    confirmacao = input(f"Deletar perfil '{profile.name}' (ID: {profile.id})? [s/N] ").strip().lower()
    if confirmacao != "s":
        print("Cancelado.")
        return

    if cloner.delete_profile(perfil_id):
        _print_ok(f"Perfil '{profile.name}' removido.")
    else:
        _print_err("Erro ao remover perfil.")


# ─── Parser principal ─────────────────────────────────────────────────────

# Type hint necessário para o argparse
from typing import Optional


def main() -> None:
    parser = argparse.ArgumentParser(
        description="🎤 Shaz AI — Clonagem de Voz",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    # ── clonar ──────────────────────────────────────────────────────
    p_clonar = subparsers.add_parser("clonar", help="Cria um perfil de voz a partir de um áudio")
    p_clonar.add_argument("--audio", "-a", required=True, help="Caminho do áudio de referência (WAV, MP3, etc.)")
    p_clonar.add_argument("--nome", "-n", required=True, help="Nome do perfil")
    p_clonar.add_argument("--lang", "-l", default="pt", help="Código do idioma (pt, en, es, ...) — padrão: pt")
    p_clonar.add_argument("--descricao", "-d", default="", help="Descrição opcional")

    # ── listar ──────────────────────────────────────────────────────
    subparsers.add_parser("listar", help="Lista todos os perfis de voz salvos")

    # ── gerar ───────────────────────────────────────────────────────
    p_gerar = subparsers.add_parser("gerar", help="Gera áudio com uma voz clonada")
    p_gerar.add_argument("--perfil", "-p", required=True, help="ID do perfil de voz")
    p_gerar.add_argument("--texto", "-t", default=None, help="Texto a sintetizar (pergunta no terminal se omitido)")
    p_gerar.add_argument("--saida", "-s", default="saida.wav", help="Arquivo de saída (padrão: saida.wav)")
    p_gerar.add_argument("--velocidade", "-v", type=float, default=1.0, help="Velocidade da fala (padrão: 1.0)")
    p_gerar.add_argument("--temperatura", type=float, default=0.75, help="Temperatura/variação da voz (padrão: 0.75)")
    p_gerar.add_argument("--reproduzir", "-r", action="store_true", help="Reproduz o áudio após gerar")

    # ── clonar-gerar ─────────────────────────────────────────────────
    p_cg = subparsers.add_parser("clonar-gerar", help="Clona voz e gera mensagem de uma vez")
    p_cg.add_argument("--audio", "-a", required=True, help="Áudio de referência")
    p_cg.add_argument("--nome", "-n", default="Voz Clonada", help="Nome do perfil")
    p_cg.add_argument("--lang", "-l", default="pt", help="Idioma")
    p_cg.add_argument("--texto", "-t", default=None, help="Texto a sintetizar")
    p_cg.add_argument("--saida", "-s", default="saida.wav", help="Arquivo de saída")
    p_cg.add_argument("--velocidade", "-v", type=float, default=1.0, help="Velocidade")
    p_cg.add_argument("--temperatura", type=float, default=0.75, help="Temperatura")
    p_cg.add_argument("--reproduzir", "-r", action="store_true", help="Reproduz após gerar")

    # ── deletar ──────────────────────────────────────────────────────
    p_del = subparsers.add_parser("deletar", help="Remove um perfil de voz")
    p_del.add_argument("--perfil", "-p", required=True, help="ID do perfil a remover")

    args = parser.parse_args()

    print()
    print("  \033[96m🎤 Shaz AI — Voice Cloner\033[0m")
    print(f"  {'─'*40}")
    print()

    if args.comando == "clonar":
        asyncio.run(cmd_clonar(args.audio, args.nome, args.lang, args.descricao))

    elif args.comando == "listar":
        cmd_listar()

    elif args.comando == "gerar":
        asyncio.run(cmd_gerar(
            perfil_id=args.perfil,
            texto=args.texto,
            saida=args.saida,
            velocidade=args.velocidade,
            temperatura=args.temperatura,
            reproduzir=args.reproduzir,
        ))

    elif args.comando == "clonar-gerar":
        asyncio.run(cmd_clonar_gerar(
            audio=args.audio,
            nome=args.nome,
            lang=args.lang,
            texto=args.texto,
            saida=args.saida,
            velocidade=args.velocidade,
            temperatura=args.temperatura,
            reproduzir=args.reproduzir,
        ))

    elif args.comando == "deletar":
        cmd_deletar(args.perfil)


if __name__ == "__main__":
    main()
