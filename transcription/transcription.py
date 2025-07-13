import whisper
import os
import subprocess
import shutil

def transcript() -> str:
    try:
        # Verificar se o ffmpeg está disponível no PATH
        ffmpeg_path = shutil.which('ffmpeg')
        print(f"[DEBUG] ffmpeg encontrado em: {ffmpeg_path}")
        
        if not ffmpeg_path:
            # Tentar adicionar possíveis locais do ffmpeg no Windows
            possible_paths = [
                r"C:\ffmpeg\bin",
                r"C:\Program Files\ffmpeg\bin",
                r"C:\Program Files (x86)\ffmpeg\bin",
                # Adicionar mais paths se necessário
            ]
            
            for path in possible_paths:
                if os.path.exists(os.path.join(path, "ffmpeg.exe")):
                    os.environ["PATH"] = path + ";" + os.environ.get("PATH", "")
                    print(f"[DEBUG] Adicionado ao PATH: {path}")
                    break
            else:
                print("[DEBUG] ffmpeg não encontrado nos locais padrão")
        
        print("[DEBUG] Iniciando carregamento do modelo...")
        model = whisper.load_model("base")
        print("[DEBUG] Modelo carregado com sucesso!")
        
        # Determinar o caminho correto do arquivo de áudio
        # Se executado diretamente, o arquivo está no mesmo diretório
        # Se executado via API, precisa do caminho relativo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        audio_file_path = os.path.join(current_dir, "NomadEngenuity_pt.wav")
        
        # Debug: imprimir informações sobre o arquivo
        print(f"[DEBUG] Diretório atual: {current_dir}")
        print(f"[DEBUG] Caminho do arquivo: {audio_file_path}")
        print(f"[DEBUG] Arquivo existe: {os.path.exists(audio_file_path)}")
        print(f"[DEBUG] Arquivo é legível: {os.access(audio_file_path, os.R_OK)}")
        print(f"[DEBUG] Tamanho do arquivo: {os.path.getsize(audio_file_path)} bytes")
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_file_path}")
        
        if not os.access(audio_file_path, os.R_OK):
            raise PermissionError(f"Sem permissão para ler o arquivo: {audio_file_path}")
        
        print("[DEBUG] Iniciando transcrição...")
        
        # Tentar normalizar o caminho para Windows
        normalized_path = os.path.normpath(audio_file_path)
        print(f"[DEBUG] Caminho normalizado: {normalized_path}")
        
        # Verificar novamente se o ffmpeg está disponível antes da transcrição
        ffmpeg_check = shutil.which('ffmpeg')
        print(f"[DEBUG] ffmpeg disponível para transcrição: {ffmpeg_check}")
        
        result = model.transcribe(normalized_path)
        print("[DEBUG] Transcrição concluída!")
        
        print("Transcrição:", result["text"])
        return result["text"]
        
    except Exception as e:
        print(f"[DEBUG] Erro na função transcript: {str(e)}")
        print(f"[DEBUG] Tipo do erro: {type(e)}")
        import traceback
        print(f"[DEBUG] Traceback completo:")
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    transcript()
