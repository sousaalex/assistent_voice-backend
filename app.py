# app.py
# Servidor FastAPI rodando na porta 8080
# BluMa | NomadEngenuity - Estrutura profissional

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import uvicorn
import os
import shutil
import tempfile
from datetime import datetime
import re
from starlette.middleware.base import BaseHTTPMiddleware
# from tts.model_tts import generate_wav_from_text  # OBSOLETO - Usando fast_tts_generate()
from llm.llm import LLM, client, tools_config, tools_functions, get_unified_system_prompt
from llm.conversation import ConversationManager

app = FastAPI(
    title="Assistent Voice API",
    description="API principal do projeto Assistent Voice - Português Brasileiro. Documentação Swagger customizada para facilitar o desenvolvimento e integração.",
    version="1.0.0",
    contact={
        "name": "BluMa | NomadEngenuity",
        "url": "https://nomadengenuity.com",
        "email": "contato@nomadengenuity.com"
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Middleware para debug de CORS (pode ser removido em produção)
class CORSDebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        method = request.method
        
        print(f"[CORS DEBUG] Método: {method}, Origin: {origin}")
        
        response = await call_next(request)
        
        # Log dos headers de resposta relacionados ao CORS
        cors_headers = {k: v for k, v in response.headers.items() if k.lower().startswith('access-control')}
        if cors_headers:
            print(f"[CORS DEBUG] Headers de resposta: {cors_headers}")
            
        return response

# Adicionar middleware de debug
app.add_middleware(CORSDebugMiddleware)

# Lista de origens permitidas para CORS
origins = [
    "https://assistent-voice.vercel.app",
    "http://assistent-voice.vercel.app",
    "http://localhost:8081",
    "https://localhost:8081",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    # Expo Go origins
    "exp://192.168.1.5:8081",
    "http://192.168.1.5:8081",
    "http://192.168.1.5:19000",
    "http://192.168.1.5:19001",
    "http://192.168.1.5:19002",
    # Para desenvolvimento
    "*"
]
# Configurar CORS com configurações mais específicas
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
)

# Configuração fixa para português
FIXED_LANGUAGE = 'p'  # Português brasileiro

# =============================================================================
# MODELOS OTIMIZADOS - CARREGADOS UMA VEZ NA INICIALIZAÇÃO
# =============================================================================
# 
# Os modelos são carregados uma única vez quando o servidor inicia,
# proporcionando performance muito superior às versões anteriores.
# 
# - whisper_model: Modelo Whisper para transcrição
# - tts_pipeline: Pipeline Kokoro para síntese de voz
# =============================================================================

# Variáveis globais para os modelos
whisper_model = None
tts_pipeline = None

# Inicializar a LLM e o gerenciador de conversas
llm_instance = LLM(client, tools_config, tools_functions)
conversation_manager = ConversationManager(max_history=None, storage_dir="conversations")  # Histórico ilimitado com persistência JSON
system_prompt = get_unified_system_prompt()

def load_whisper_model():
    """Carrega o modelo Whisper uma única vez na inicialização do servidor."""
    global whisper_model
    if whisper_model is None:
        print("[SERVIDOR] 🎤 Carregando modelo Whisper...")
        import whisper
        whisper_model = whisper.load_model("small")
        print("[SERVIDOR] ✅ Modelo Whisper carregado com sucesso!")
    return whisper_model

def load_tts_pipeline():
    """Carrega o pipeline TTS uma única vez na inicialização do servidor."""
    global tts_pipeline
    if tts_pipeline is None:
        print("[SERVIDOR] 🔊 Carregando pipeline TTS...")
        from kokoro import KPipeline
        tts_pipeline = KPipeline(lang_code="p")
        print("[SERVIDOR] ✅ Pipeline TTS carregado com sucesso!")
    return tts_pipeline

def setup_ffmpeg():
    """Configura o ffmpeg para o Whisper funcionar corretamente."""
    print("[SERVIDOR] 🔧 Verificando ffmpeg...")
    
    # Verificar se o ffmpeg está disponível no PATH
    ffmpeg_path = shutil.which('ffmpeg')
    print(f"[SERVIDOR] ffmpeg encontrado em: {ffmpeg_path}")
    
    if not ffmpeg_path:
        print("[SERVIDOR] ⚠️ ffmpeg não encontrado no PATH, tentando localizar...")
        
        # Tentar adicionar possíveis locais do ffmpeg no Windows
        possible_paths = [
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
            r"C:\Program Files (x86)\ffmpeg\bin",
            r"C:\Users\{}\AppData\Local\ffmpeg\bin".format(os.getenv('USERNAME', '')),
            # Adicionar mais paths se necessário
        ]
        
        for path in possible_paths:
            if os.path.exists(os.path.join(path, "ffmpeg.exe")):
                os.environ["PATH"] = path + ";" + os.environ.get("PATH", "")
                print(f"[SERVIDOR] ✅ Adicionado ao PATH: {path}")
                break
        else:
            print("[SERVIDOR] ❌ ffmpeg não encontrado! O Whisper pode não funcionar corretamente.")
            print("[SERVIDOR] 💡 Instale o ffmpeg em: https://ffmpeg.org/download.html")
    
    # Verificar novamente após tentativas
    final_ffmpeg_path = shutil.which('ffmpeg')
    if final_ffmpeg_path:
        print(f"[SERVIDOR] ✅ ffmpeg configurado: {final_ffmpeg_path}")
    else:
        print("[SERVIDOR] ⚠️ ffmpeg ainda não encontrado após tentativas")

# Carregar os modelos na inicialização
print("[SERVIDOR] 🚀 Inicializando modelos...")
setup_ffmpeg()
load_whisper_model()
load_tts_pipeline()
print("[SERVIDOR] ✅ Todos os modelos inicializados!")

class ConversationContext(BaseModel):
    session_id: str
    conversation_id: str
    message_id: str
    timezone: str = Field(default="America/Sao_Paulo")
    locale: str = Field(default="pt-BR")
    user_agent: Optional[str] = None
    platform: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    is_mobile: bool = Field(default=False)

class TTSRequest(BaseModel):
    context: ConversationContext

class SimpleTTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None

def process_text_for_tts(text: str) -> str:
    """
    Processa o texto para melhorar a pronúncia do TTS,
    quebrando em linhas nas pontuações (exceto vírgulas).
    """
    # Substitui reticências por quebra de linha
    text = text.replace("...", "...\n")
    
    # Adiciona quebra de linha após pontuação seguida de espaço
    text = re.sub(r'([.!?:]) ', r'\1\n', text)
    
    # Remove linhas vazias extras
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()

def fast_transcript(audio_file_path: str) -> str:
    """
    =============================================================================
    FUNÇÃO OTIMIZADA DE TRANSCRIÇÃO
    =============================================================================
    
    Versão otimizada que usa o modelo Whisper já carregado na inicialização.
    Performance muito superior à versão original que carregava o modelo a cada chamada.
    
    Args:
        audio_file_path (str): Caminho para o arquivo de áudio WAV
        
    Returns:
        str: Texto transcrito do áudio
        
    Raises:
        Exception: Se o modelo não foi carregado ou erro na transcrição
    """
    global whisper_model
    
    if whisper_model is None:
        print("[ERRO] Modelo Whisper não foi carregado!")
        raise Exception("Modelo Whisper não inicializado")
    
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
        
        print("[DEBUG] Iniciando transcrição otimizada...")
        result = whisper_model.transcribe(audio_file_path)
        print("[DEBUG] Transcrição otimizada concluída!")
        return result["text"]
    except Exception as e:
        print(f"[DEBUG] Erro na transcrição otimizada: {str(e)}")
        raise e

def fast_tts_generate(text: str, voice: str = "pm_santa") -> str:
    """
    =============================================================================
    FUNÇÃO OTIMIZADA DE TTS
    =============================================================================
    
    Versão otimizada que usa o pipeline Kokoro já carregado na inicialização.
    Performance muito superior à versão original que criava o pipeline a cada chamada.
    
    Args:
        text (str): Texto para converter em áudio
        voice (str): Voz a usar (padrão: "pm_santa")
        
    Returns:
        str: Caminho do arquivo de áudio gerado
        
    Raises:
        Exception: Se o pipeline não foi carregado ou erro na geração
    """
    global tts_pipeline
    
    if tts_pipeline is None:
        print("[ERRO] Pipeline TTS não foi carregado!")
        raise Exception("Pipeline TTS não inicializado")
    
    try:
        print("[DEBUG] Iniciando geração de áudio otimizada...")
        
        # Gerar áudio
        generator = tts_pipeline(text, voice)
        
        audio_chunks = []
        for i, (gs, ps, audio) in enumerate(generator):
            audio_chunks.append(audio)
        
        if not audio_chunks:
            raise RuntimeError("Falha na geração do áudio - nenhum chunk gerado.")
        
        # Concatenar chunks de áudio
        import numpy as np
        audio_completo = np.concatenate(audio_chunks)
        
        # Criar arquivo temporário
        import tempfile
        import soundfile as sf
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            wav_path = temp_file.name
        
        # Salvar áudio no arquivo temporário
        sf.write(wav_path, audio_completo, 24000)
        
        print("[DEBUG] Geração de áudio otimizada concluída!")
        return wav_path
        
    except Exception as e:
        print(f"[DEBUG] Erro na geração de áudio otimizada: {str(e)}")
        raise e

@app.get("/", tags=["Root"])
def root():
    return {"message": "Servidor FastAPI rodando na porta 8765! 🇧🇷 Português Brasileiro"}

@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint de health check para verificar se o servidor está funcionando."""
    ffmpeg_available = shutil.which('ffmpeg') is not None
    
    return {
        "status": "healthy",
        "message": "Servidor funcionando corretamente",
        "whisper_model_loaded": whisper_model is not None,
        "tts_pipeline_loaded": tts_pipeline is not None,
        "ffmpeg_available": ffmpeg_available,
        "models_ready": whisper_model is not None and tts_pipeline is not None,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.options("/tts", tags=["TTS"])
async def tts_options():
    """Endpoint OPTIONS para requisições preflight CORS."""
    return {"message": "OK"}

@app.post("/tts", tags=["TTS"], summary="Processa áudio, transcreve, processa na LLM e gera áudio de resposta", response_description="Áudio mp3 gerado com a resposta da LLM")
async def tts_endpoint(
    audio_file: UploadFile = File(..., description="Arquivo de áudio WAV para transcrição"),
    session_id: str = Form("", description="ID da sessão enviado via FormData"),
    conversation_id: str = Form("", description="ID da conversa enviado via FormData"),
    message_id: str = Form("", description="ID da mensagem enviado via FormData"),
    timezone: str = Form("America/Sao_Paulo", description="Timezone enviado via FormData"),
    locale: str = Form("pt-BR", description="Locale enviado via FormData")
):
    """
    Novo fluxo completo de processamento de áudio:
    1. Recebe arquivo de áudio WAV
    2. Transcreve o áudio usando whisper
    3. Processa a transcrição na LLM mantendo o contexto da conversa
    4. Converte a resposta da LLM em áudio usando TTS
    5. Retorna o arquivo de áudio mp3 da resposta
    """
    
    # ==================== LOGS DE ENTRADA ====================
    print("\n" + "="*80)
    print("[DEBUG] ===== NOVA REQUISIÇÃO /tts =====")
    print(f"[DEBUG] Data/Hora: {datetime.utcnow().isoformat()}")
    print("="*80)
    
    # Logs do arquivo de áudio
    print(f"[DEBUG] === ARQUIVO DE ÁUDIO ===")
    print(f"[DEBUG] Filename: {audio_file.filename}")
    print(f"[DEBUG] Content-Type: {audio_file.content_type}")
    print(f"[DEBUG] Size: {audio_file.size if hasattr(audio_file, 'size') else 'N/A'} bytes")
    
    # Logs dos parâmetros recebidos
    print(f"[DEBUG] === PARÂMETROS RECEBIDOS VIA FORMDATA ===")
    print(f"[DEBUG] session_id: '{session_id}' (tipo: {type(session_id)}, vazio: {not session_id})")
    print(f"[DEBUG] conversation_id: '{conversation_id}' (tipo: {type(conversation_id)}, vazio: {not conversation_id})")
    print(f"[DEBUG] message_id: '{message_id}' (tipo: {type(message_id)}, vazio: {not message_id})")
    print(f"[DEBUG] timezone: '{timezone}' (tipo: {type(timezone)})")
    print(f"[DEBUG] locale: '{locale}' (tipo: {type(locale)})")
    print("[DEBUG] ✅ Dados recebidos via FormData corretamente!")
    
    # Validar o arquivo de áudio
    if not audio_file.filename.lower().endswith('.wav'):
        print(f"[DEBUG] ERRO: Arquivo não é WAV: {audio_file.filename}")
        raise HTTPException(status_code=400, detail="Apenas arquivos WAV são suportados.")
    
    # Criar contexto da conversa
    context = ConversationContext(
        session_id=session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        conversation_id=conversation_id or f"conv_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        message_id=message_id or f"msg_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        timezone=timezone,
        locale=locale
    )
    
    # DEBUG: Logs do contexto FINAL
    print(f"[DEBUG] === CONTEXTO FINAL CRIADO ===")
    print(f"[DEBUG] Session ID FINAL: '{context.session_id}' (gerado automaticamente: {not session_id})")
    print(f"[DEBUG] Conversation ID FINAL: '{context.conversation_id}' (gerado automaticamente: {not conversation_id})")
    print(f"[DEBUG] Message ID FINAL: '{context.message_id}' (gerado automaticamente: {not message_id})")
    print(f"[DEBUG] Timezone FINAL: '{context.timezone}'")
    print(f"[DEBUG] Locale FINAL: '{context.locale}'")
    
    # Log adicional sobre a origem dos dados
    if session_id and conversation_id and message_id:
        print("[DEBUG] ✅ Todos os IDs foram recebidos do frontend via FormData!")
    else:
        print("[DEBUG] ⚠️  Alguns IDs foram gerados automaticamente pelo backend")
    
    print("="*80 + "\n")
    
    temp_audio_path = None
    try:
        # Salvar o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_audio_path = temp_file.name
        
        print(f"[DEBUG] Arquivo de áudio salvo em: {temp_audio_path}")
        print(f"[DEBUG] Tamanho do arquivo salvo: {os.path.getsize(temp_audio_path)} bytes")
        
        # Transcrever o áudio (versão otimizada)
        print("[DEBUG] Iniciando transcrição otimizada do áudio...")
        transcribed_text = fast_transcript(temp_audio_path)
        print(f"[DEBUG] Texto transcrito: '{transcribed_text}'")
        
        if not transcribed_text or not transcribed_text.strip():
            raise HTTPException(status_code=400, detail="Não foi possível transcrever o áudio ou o áudio está vazio.")
        
        # Obter histórico da conversa
        print(f"[DEBUG] === VERIFICANDO HISTÓRICO ===")
        print(f"[DEBUG] Procurando histórico para session_id: '{context.session_id}'")
        conversation_history = conversation_manager.get_conversation_messages(context.session_id)
        
        # DEBUG: Logs do histórico
        print(f"[DEBUG] Histórico encontrado: {len(conversation_history)} mensagens")
        print(f"[DEBUG] Todas as sessões ativas: {list(conversation_manager.conversations.keys())}")
        if conversation_history:
            print("[DEBUG] Histórico completo:")
            for i, msg in enumerate(conversation_history):
                print(f"  {i+1}. {msg['role']}: {msg['content'][:50]}...")
        else:
            print("[DEBUG] Nenhum histórico encontrado para esta sessão")
        
        # Montar mensagens com histórico
        messages = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]
        
        # Adicionar histórico completo (já limitado pelo ConversationManager)
        if conversation_history:
            messages.extend(conversation_history)
        
        # Adicionar mensagem atual (texto transcrito)
        messages.append({
            "role": "user",
            "content": transcribed_text
        })
        
        # DEBUG: Logs das mensagens para LLM
        print(f"[DEBUG] === ENVIANDO PARA LLM ===")
        print(f"[DEBUG] Total de mensagens para LLM: {len(messages)}")
        print("[DEBUG] Mensagens para LLM:")
        for i, msg in enumerate(messages):
            role = msg['role']
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            print(f"  {i+1}. {role}: {content}")
        
        # Obter resposta da LLM
        print("[DEBUG] Processando na LLM...")
        llm_response = llm_instance.run(messages)
        print("==================RESPOSTA DA LLM=====================\n\n")
        print(f"{llm_response}\n\n")
        print("==================FIM RESPOSTA DA LLM=====================")

        if not llm_response or not llm_response.strip():
            raise HTTPException(status_code=500, detail="LLM não gerou uma resposta válida.")
        
        # Processar texto para melhorar pronúncia do TTS
        processed_response = process_text_for_tts(llm_response)
        
        # Atualizar histórico da conversa
        print(f"[DEBUG] === SALVANDO NO HISTÓRICO ===")
        print(f"[DEBUG] Salvando no histórico - Session: '{context.session_id}'")
        print(f"[DEBUG] Mensagem do usuário: '{transcribed_text}'")
        print(f"[DEBUG] Resposta do assistente: '{llm_response[:100]}...'")
        
        conversation_manager.add_message(
            context=context.dict(),
            user_message=transcribed_text,
            assistant_message=llm_response
        )
        
        # DEBUG: Verificar se foi salvo
        updated_history = conversation_manager.get_conversation_messages(context.session_id)
        print(f"[DEBUG] Histórico após salvar: {len(updated_history)} mensagens")
        print(f"[DEBUG] Últimas 2 mensagens salvas:")
        for msg in updated_history[-2:]:
            print(f"  - {msg['role']}: {msg['content'][:50]}...")
        
        print(f"[DEBUG] === SESSÕES ATIVAS APÓS SALVAR ===")
        print(f"[DEBUG] Todas as sessões: {list(conversation_manager.conversations.keys())}")
        
        # Converter resposta processada para áudio (versão otimizada)
        print("[DEBUG] Gerando áudio da resposta (versão otimizada)...")
        wav_path = fast_tts_generate(llm_response)
        
        # Ler e retornar o arquivo de áudio
        with open(wav_path, "rb") as f:
            audio_bytes = f.read()
        
        # Limpar arquivo de áudio gerado
        os.remove(wav_path)
        
        # Criar resposta com headers de CORS explícitos
        response = Response(content=audio_bytes, media_type="audio/mpeg")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        print(f"[DEBUG] === RESPOSTA ENVIADA ===")
        print(f"[DEBUG] Tamanho do áudio de resposta: {len(audio_bytes)} bytes")
        print("="*80 + "\n")
        
        return response
        
    except Exception as e:
        print(f"[DEBUG] === ERRO NO FLUXO ===")
        print(f"[DEBUG] Erro no fluxo completo: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro no fluxo de processamento: {str(e)}")
    
    finally:
        # Limpar arquivo de áudio temporário
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            print(f"[DEBUG] Arquivo temporário removido: {temp_audio_path}")

@app.get("/conversation/{session_id}", tags=["Conversation"])
def get_conversation(session_id: str):
    """Retorna o resumo e histórico de uma conversa específica."""
    summary = conversation_manager.get_conversation_summary(session_id)
    if not summary['message_count']:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    return summary

@app.delete("/conversation/{session_id}", tags=["Conversation"])
def clear_conversation(session_id: str):
    """Limpa o histórico de uma conversa específica."""
    if conversation_manager.clear_conversation(session_id):
        return {"message": "Conversa limpa com sucesso"}
    raise HTTPException(status_code=404, detail="Conversa não encontrada")

@app.get("/debug/history/{session_id}", tags=["Debug"])
def debug_history(session_id: str):
    """Endpoint de debug para verificar o histórico de uma sessão."""
    conversation_history = conversation_manager.get_conversation_messages(session_id)
    session_info = conversation_manager.get_session_info(session_id)
    
    return {
        "session_id": session_id,
        "message_count": len(conversation_history),
        "session_info": session_info,
        "all_active_sessions": list(conversation_manager.conversations.keys()),
        "conversation_history": conversation_history
    }

@app.get("/debug/all-sessions", tags=["Debug"])
def debug_all_sessions():
    """Endpoint de debug para ver todas as sessões ativas."""
    all_sessions = {}
    for session_id in conversation_manager.conversations.keys():
        messages = conversation_manager.get_conversation_messages(session_id)
        all_sessions[session_id] = {
            "message_count": len(messages),
            "last_messages": messages[-2:] if len(messages) >= 2 else messages
        }
    
    return {
        "total_sessions": len(all_sessions),
        "sessions": all_sessions
    }

@app.get("/debug/storage-info", tags=["Debug"])
def debug_storage_info():
    """Endpoint de debug para ver informações sobre o armazenamento JSON."""
    import os
    
    storage_dir = "conversations"
    if not os.path.exists(storage_dir):
        return {
            "storage_dir": storage_dir,
            "exists": False,
            "files": [],
            "total_size": 0
        }
    
    files = []
    total_size = 0
    
    for filename in os.listdir(storage_dir):
        if filename.endswith('.json'):
            file_path = os.path.join(storage_dir, filename)
            file_size = os.path.getsize(file_path)
            files.append({
                "filename": filename,
                "size_bytes": file_size,
                "size_mb": round(file_size / 1024 / 1024, 2)
            })
            total_size += file_size
    
    return {
        "storage_dir": storage_dir,
        "exists": True,
        "files": files,
        "total_files": len(files),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / 1024 / 1024, 2)
    }

@app.options("/transcript", tags=["Transcription"])
async def transcript_options():
    """Endpoint OPTIONS para requisições preflight CORS."""
    return {"message": "OK"}

@app.post("/transcript", tags=["Transcription"], summary="Executa transcrição de áudio", response_description="Texto transcrito do áudio")
async def transcript_endpoint(
    audio_file: UploadFile = File(..., description="Arquivo de áudio WAV para transcrição")
):
    """
    Endpoint que transcreve um arquivo de áudio WAV usando o whisper.
    
    Retorna o texto transcrito do arquivo de áudio enviado.
    """
    
    # Validar o arquivo de áudio
    if not audio_file.filename.lower().endswith('.wav'):
        raise HTTPException(status_code=400, detail="Apenas arquivos WAV são suportados.")
    
    temp_audio_path = None
    try:
        # Salvar o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_audio_path = temp_file.name
        
        print(f"[DEBUG] Arquivo de áudio salvo em: {temp_audio_path}")
        
        # Transcrever o áudio (versão otimizada)
        transcribed_text = fast_transcript(temp_audio_path)
        
        return {
            "status": "success",
            "transcribed_text": transcribed_text,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        print(f"[DEBUG] Erro na transcrição: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro na transcrição: {str(e)}")
    
    finally:
        # Limpar arquivo de áudio temporário
        if temp_audio_path and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            print(f"[DEBUG] Arquivo temporário removido: {temp_audio_path}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[SERVIDOR] Iniciando servidor na porta {port}")
    print(f"[CORS] Origens permitidas: {origins}")
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port, 
    )
