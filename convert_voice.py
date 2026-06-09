import sys
import os
import subprocess
from pathlib import Path

# Fix encoding on Windows for unicode character prints (e.g. Japanese file names)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def main():
    if len(sys.argv) < 2:
        print("Uso: python convert_voice.py <caminho_do_arquivo.mp3>")
        print("Exemplo: python convert_voice.py C:\\Users\\lucas\\Downloads\\voz_da_shaz.mp3")
        sys.exit(1)
        
    mp3_path = sys.argv[1]
    if not os.path.exists(mp3_path):
        print(f"ERRO: O arquivo '{mp3_path}' não foi encontrado.")
        sys.exit(1)
        
    dest_wav = Path(r"c:\Users\lucas\OneDrive\Área de Trabalho\shaz_ai\assets\voices\shaz_reference.wav")
    dest_wav.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Convertendo '{mp3_path}'...")
    print(f"Destino: '{dest_wav}'")
    
    cmd = [
        "ffmpeg",
        "-y",               # Sobrescreve se já existir
        "-i", mp3_path,
        "-acodec", "pcm_s16le",
        "-ac", "1",         # Mono (necessário para XTTS)
        "-ar", "22050",     # 22.05kHz (ideal para XTTS)
        str(dest_wav)
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("\n🎉 SUCESSO! A voz foi convertida e configurada como voz de referência para clonagem.")
        print("Para ativá-la, certifique-se de que a engine 'xtts' está selecionada no arquivo shaz/config/voice_config.json")
    except FileNotFoundError:
        print("\nERRO: O FFmpeg não foi encontrado no sistema. Por favor, instale o FFmpeg ou converta o MP3 para WAV online.")
    except subprocess.CalledProcessError as e:
        print(f"\nERRO: O FFmpeg falhou ao converter o arquivo. Detalhes: {e}")

if __name__ == "__main__":
    main()
