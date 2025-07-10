from kokoro import KPipeline
import soundfile as sf
import numpy as np
import tempfile
import os
from typing import Optional



def generate_wav_from_text(text: str, language: str = 'p', voice: Optional[str] = None) -> str:
    """
    Gera arquivo WAV a partir de texto usando Kokoro TTS.
    OTIMIZADO PARA PORTUGUÊS BRASILEIRO.
    
    Args:
        text (str): Texto para converter em áudio
        language (str): Código do idioma (padrão 'p' para português)
        voice (str, optional): Voz específica a usar. Se None, usa voz padrão.
    
    Returns:
        str: Caminho do arquivo WAV gerado
        
    Raises:
        ValueError: Se idioma não suportado ou texto vazio
        RuntimeError: Se falha na geração do áudio
    """
    
    if not text or not text.strip():
        raise ValueError("Texto não pode ser vazio.")
    
    
    try:
        # Configurar pipeline para o idioma
        pipeline = KPipeline(lang_code="p")
        voice="pm_santa"
        
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
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            wav_path = temp_file.name
        
        # Salvar áudio no arquivo temporário
        sf.write(wav_path, audio_completo, 24000)
        
        return wav_path
        
    except Exception as e:
        raise RuntimeError(f"Erro ao gerar áudio TTS: {str(e)}")

