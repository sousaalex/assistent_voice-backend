# =============================================================================
# MÓDULO TTS - VERSÃO OBSOLETA
# =============================================================================
# 
# Este módulo foi substituído pela implementação otimizada no app.py
# O carregamento do pipeline TTS agora é feito na inicialização
# do servidor para melhor performance.
# 
# Para TTS otimizado, use: fast_tts_generate() no app.py
# =============================================================================

from kokoro import KPipeline
import soundfile as sf
import numpy as np
import tempfile
import os
from typing import Optional

# =============================================================================
# CÓDIGO OBSOLETO - MANTIDO PARA REFERÊNCIA
# =============================================================================

# Variável global para armazenar o pipeline TTS
_tts_pipeline = None

def get_tts_pipeline():
    """Retorna o pipeline TTS, carregando-o apenas uma vez."""
    global _tts_pipeline
    if _tts_pipeline is None:
        print("[DEBUG] Iniciando carregamento do pipeline TTS...")
        _tts_pipeline = KPipeline(lang_code="p")
        print("[DEBUG] Pipeline TTS carregado com sucesso!")
    return _tts_pipeline

def generate_wav_from_text(text: str, language: str = 'p', voice: str = "pm_santa") -> str:
    """
    FUNÇÃO OBSOLETA - Use fast_tts_generate() no app.py para melhor performance
    
    Gera arquivo mp3 a partir de texto usando Kokoro TTS.
    OTIMIZADO PARA PORTUGUÊS BRASILEIRO.
    
    Args:
        text (str): Texto para converter em áudio
        language (str): Código do idioma (padrão 'p' para português)
        voice (str, optional): Voz específica a usar. Se None, usa voz padrão.
    
    Returns:
        str: Caminho do arquivo mp3 gerado
        
    Raises:
        ValueError: Se idioma não suportado ou texto vazio
        RuntimeError: Se falha na geração do áudio
    """
    
    if not text or not text.strip():
        raise ValueError("Texto não pode ser vazio.")
    
    try:
        # Obter pipeline já carregado (otimizado)
        pipeline = get_tts_pipeline()
        
        # Gerar áudio
        generator = pipeline(text, voice)
        
        audio_chunks = []
        for i, (gs, ps, audio) in enumerate(generator):
            audio_chunks.append(audio)
        
        if not audio_chunks:
            raise RuntimeError("Falha na geração do áudio - nenhum chunk gerado.")
        
        # Concatenar chunks de áudio
        audio_completo = np.concatenate(audio_chunks)
        
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            wav_path = temp_file.name
        
        # Salvar áudio no arquivo temporário
        sf.write(wav_path, audio_completo, 24000)
        
        return wav_path
        
    except Exception as e:
        raise RuntimeError(f"Erro ao gerar áudio TTS: {str(e)}")

# Inicializar o pipeline quando o módulo for importado
# print("[DEBUG] Módulo TTS importado - inicializando pipeline...")
# get_tts_pipeline()
# print("[DEBUG] Pipeline TTS inicializado com sucesso!")

