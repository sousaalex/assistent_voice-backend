from typing import Dict, List, Optional
from datetime import datetime
import json
import os
from collections import defaultdict

class ConversationManager:
    def __init__(self, max_history: Optional[int] = None, storage_dir: str = "conversations"):
        """
        Inicializa o gerenciador de conversas com persistência JSON.
        
        Args:
            max_history: Número máximo de pares de mensagens (usuário + assistente) a manter no histórico.
                        Se None, mantém histórico ilimitado.
                        Por exemplo, max_history=10 manterá as últimas 20 mensagens (10 do usuário + 10 do assistente)
            storage_dir: Diretório onde salvar os arquivos JSON de conversas
        """
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history = max_history
        self.session_metadata: Dict[str, Dict] = {}
        self.storage_dir = storage_dir
        
        # Criar diretório de armazenamento se não existir
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Carregar conversas existentes
        self._load_conversations()

    def add_message(self, context: Dict, user_message: str, assistant_message: Optional[str] = None) -> List[Dict]:
        """
        Adiciona uma nova mensagem à conversa e retorna o histórico atualizado.
        O histórico é automaticamente limitado pelo max_history definido na inicialização.
        Se max_history for None, mantém histórico ilimitado.
        """
        session_id = context.get('session_id')
        message_id = context.get('message_id')
        timestamp = context.get('timestamp', datetime.utcnow().isoformat())

        # Atualiza ou cria metadados da sessão
        if session_id not in self.session_metadata:
            self.session_metadata[session_id] = {
                'conversation_id': context.get('conversation_id'),
                'timezone': context.get('timezone'),
                'locale': context.get('locale'),
                'platform': context.get('platform'),
                'user_agent': context.get('user_agent'),
                'is_mobile': context.get('is_mobile', False),
                'created_at': timestamp,
                'last_interaction': timestamp
            }
        else:
            self.session_metadata[session_id]['last_interaction'] = timestamp

        # Adiciona mensagem do usuário
        self.conversations[session_id].append({
            'role': 'user',
            'content': user_message,
            'message_id': message_id,
            'timestamp': timestamp
        })

        # Adiciona resposta do assistente se houver
        if assistant_message:
            self.conversations[session_id].append({
                'role': 'assistant',
                'content': assistant_message,
                'message_id': f"response-{message_id}",
                'timestamp': datetime.utcnow().isoformat()
            })

        # Mantém apenas o número máximo de mensagens definido se max_history não for None
        if self.max_history is not None and len(self.conversations[session_id]) > self.max_history * 2:  # * 2 para contar pares de mensagens
            self.conversations[session_id] = self.conversations[session_id][-self.max_history * 2:]

        # Salvar automaticamente após adicionar mensagem
        self._save_conversation(session_id)

        return self.get_conversation_messages(session_id)

    def get_conversation_messages(self, session_id: str) -> List[Dict]:
        """
        Retorna as mensagens da conversa em formato adequado para a LLM.
        O número de mensagens é automaticamente limitado pelo max_history.
        """
        return self.conversations.get(session_id, [])

    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Retorna informações sobre a sessão."""
        return self.session_metadata.get(session_id)

    def clear_conversation(self, session_id: str) -> bool:
        """Limpa o histórico de uma conversa específica."""
        if session_id in self.conversations:
            del self.conversations[session_id]
            # Remover arquivo JSON também
            self._delete_conversation_file(session_id)
            return True
        return False

    def get_conversation_summary(self, session_id: str) -> Dict:
        """Retorna um resumo da conversa."""
        messages = self.conversations.get(session_id, [])
        metadata = self.session_metadata.get(session_id, {})
        
        return {
            'session_id': session_id,
            'message_count': len(messages),
            'first_interaction': messages[0]['timestamp'] if messages else None,
            'last_interaction': messages[-1]['timestamp'] if messages else None,
            'metadata': metadata
        }
    
    def _get_conversation_file_path(self, session_id: str) -> str:
        """Retorna o caminho do arquivo JSON para uma sessão."""
        # Sanitizar o session_id para usar como nome de arquivo
        safe_session_id = "".join(c for c in session_id if c.isalnum() or c in ('-', '_'))
        return os.path.join(self.storage_dir, f"{safe_session_id}.json")
    
    def _save_conversation(self, session_id: str) -> None:
        """Salva uma conversa em arquivo JSON."""
        try:
            file_path = self._get_conversation_file_path(session_id)
            conversation_data = {
                'session_id': session_id,
                'messages': self.conversations[session_id],
                'metadata': self.session_metadata.get(session_id, {})
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
                
            print(f"[DEBUG] ✅ Conversa salva em: {file_path}")
            
        except Exception as e:
            print(f"[DEBUG] ⚠️  Erro ao salvar conversa {session_id}: {str(e)}")
    
    def _load_conversations(self) -> None:
        """Carrega todas as conversas dos arquivos JSON."""
        try:
            if not os.path.exists(self.storage_dir):
                print(f"[DEBUG] Diretório de conversas não encontrado: {self.storage_dir}")
                return
            
            loaded_count = 0
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    try:
                        file_path = os.path.join(self.storage_dir, filename)
                        with open(file_path, 'r', encoding='utf-8') as f:
                            conversation_data = json.load(f)
                        
                        session_id = conversation_data.get('session_id')
                        if session_id:
                            self.conversations[session_id] = conversation_data.get('messages', [])
                            self.session_metadata[session_id] = conversation_data.get('metadata', {})
                            loaded_count += 1
                            print(f"[DEBUG] ✅ Conversa carregada: {session_id} ({len(self.conversations[session_id])} mensagens)")
                    
                    except Exception as e:
                        print(f"[DEBUG] ⚠️  Erro ao carregar arquivo {filename}: {str(e)}")
            
            print(f"[DEBUG] 📁 Total de conversas carregadas: {loaded_count}")
            
        except Exception as e:
            print(f"[DEBUG] ⚠️  Erro ao carregar conversas: {str(e)}")
    
    def _delete_conversation_file(self, session_id: str) -> None:
        """Remove o arquivo JSON de uma conversa."""
        try:
            file_path = self._get_conversation_file_path(session_id)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[DEBUG] ✅ Arquivo de conversa removido: {file_path}")
        except Exception as e:
            print(f"[DEBUG] ⚠️  Erro ao remover arquivo da conversa {session_id}: {str(e)}") 