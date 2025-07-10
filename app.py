# app.py
# Servidor FastAPI rodando na porta 8080
# BluMa | NomadEngenuity - Estrutura profissional

from fastapi import FastAPI, HTTPException, UploadFile, File, Response, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
import uvicorn
import os
import shutil
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from tts.model_tts import generate_wav_from_text
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
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",  # Para desenvolvimento com HTTPS
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

# Inicializar a LLM e o gerenciador de conversas
llm_instance = LLM(client, tools_config, tools_functions)
conversation_manager = ConversationManager(max_history=10)
system_prompt = get_unified_system_prompt()

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
    text: str
    context: ConversationContext

class SimpleTTSRequest(BaseModel):
    text: str
    voice: Optional[str] = None

@app.get("/", tags=["Root"])
def root():
    return {"message": "Servidor FastAPI rodando na porta 8765! 🇧🇷 Português Brasileiro"}

@app.get("/health", tags=["Health"])
def health_check():
    """Endpoint de health check para verificar se o servidor está funcionando."""
    return {
        "status": "healthy",
        "message": "Servidor funcionando corretamente",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.options("/tts", tags=["TTS"])
async def tts_options():
    """Endpoint OPTIONS para requisições preflight CORS."""
    return {"message": "OK"}

@app.post("/tts", tags=["TTS"], summary="Processa pergunta na LLM e gera áudio em português", response_description="Áudio WAV gerado com a resposta da LLM")
def tts_endpoint(request: TTSRequest):
    """
    Recebe uma pergunta em português, processa na LLM mantendo o contexto da conversa, e retorna o áudio gerado da resposta.
    
    Fluxo completo (apenas português):
    1. Recebe a pergunta e contexto
    2. Processa na LLM para gerar resposta, considerando histórico
    3. Converte a resposta da LLM em áudio usando TTS
    4. Retorna o arquivo de áudio WAV
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Pergunta não pode ser vazia.")
    
    try:
        # Obter histórico da conversa
        conversation_history = conversation_manager.get_conversation_messages(request.context.session_id)
        
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
        
        # Adicionar mensagem atual
        messages.append({
            "role": "user",
            "content": request.text
        })
        
        # Obter resposta da LLM
        llm_response = llm_instance.run(messages)
        
        if not llm_response or not llm_response.strip():
            raise HTTPException(status_code=500, detail="LLM não gerou uma resposta válida.")
        
        # Atualizar histórico da conversa
        conversation_manager.add_message(
            context=request.context.dict(),
            user_message=request.text,
            assistant_message=llm_response
        )
        
        # Converter resposta para áudio
        wav_path = generate_wav_from_text(llm_response, language=FIXED_LANGUAGE)
        
        # Ler e retornar o arquivo de áudio
        with open(wav_path, "rb") as f:
            audio_bytes = f.read()
        
        # Limpar arquivo temporário
        os.remove(wav_path)
        
        # Criar resposta com headers de CORS explícitos
        response = Response(content=audio_bytes, media_type="audio/wav")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no fluxo LLM + TTS: {str(e)}")

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"[SERVIDOR] Iniciando servidor na porta {port}")
    print(f"[CORS] Origens permitidas: {origins}")
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,
        access_log=True,
        log_level="info"
    )
