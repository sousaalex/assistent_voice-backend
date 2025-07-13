# =============================================================================
# MÓDULO TRANSCRIPTE - VERSÃO OBSOLETA
# =============================================================================
# 
# Este módulo foi substituído pela implementação otimizada no app.py
# O carregamento do modelo e configuração do ffmpeg agora é feito na inicialização
# do servidor para melhor performance.
# 
# Para transcrição otimizada, use: fast_transcript() no app.py
# =============================================================================

import whisper
import os
import subprocess
import shutil

# =============================================================================
# CÓDIGO OBSOLETO - MANTIDO PARA REFERÊNCIA
# =============================================================================

# Variável global para armazenar o modelo carregado
_model = None

def get_model():
    """Retorna o modelo Whisper, carregando-o apenas uma vez."""
    global _model
    if _model is None:
        print("[DEBUG] Iniciando carregamento do modelo...")
        _model = whisper.load_model("large-v3-turbo")
        print("[DEBUG] Modelo carregado com sucesso!")
    return _model

# Inicializar o modelo quando o módulo for importado
# print("[DEBUG] Módulo transcripte importado - inicializando modelo...")
# get_model()
# print("[DEBUG] Modelo inicializado com sucesso!")

def transcript(audio_file_path: str = None) -> str:
    """
    FUNÇÃO OBSOLETA - Use fast_transcript() no app.py para melhor performance
    
    Esta função carrega o modelo a cada chamada, o que é ineficiente.
    A versão otimizada está no app.py com carregamento único na inicialização.
    """
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
        
        # Obter o modelo (carregado apenas uma vez)
        model = get_model()
        
        # Se não foi fornecido um caminho, usar o arquivo padrão
        if audio_file_path is None:
           return None
        
        # Debug: imprimir informações sobre o arquivo
        # print(f"[DEBUG] Caminho do arquivo: {audio_file_path}")
        # print(f"[DEBUG] Arquivo existe: {os.path.exists(audio_file_path)}")
        # print(f"[DEBUG] Arquivo é legível: {os.access(audio_file_path, os.R_OK)}")
        # print(f"[DEBUG] Tamanho do arquivo: {os.path.getsize(audio_file_path)} bytes")
        
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
