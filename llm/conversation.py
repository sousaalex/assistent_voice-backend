from typing import Dict, List, Optional
from datetime import datetime
import json
from collections import defaultdict

class ConversationManager:
    def __init__(self, max_history: int = 10):
        """
        Inicializa o gerenciador de conversas.
        
        Args:
            max_history: Número máximo de pares de mensagens (usuário + assistente) a manter no histórico.
                        Por exemplo, max_history=10 manterá as últimas 20 mensagens (10 do usuário + 10 do assistente)
        """
        self.conversations: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history = max_history
        self.session_metadata: Dict[str, Dict] = {}

    def add_message(self, context: Dict, user_message: str, assistant_message: Optional[str] = None) -> List[Dict]:
        """
        Adiciona uma nova mensagem à conversa e retorna o histórico atualizado.
        O histórico é automaticamente limitado pelo max_history definido na inicialização.
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

        # Mantém apenas o número máximo de mensagens definido
        if len(self.conversations[session_id]) > self.max_history * 2:  # * 2 para contar pares de mensagens
            self.conversations[session_id] = self.conversations[session_id][-self.max_history * 2:]

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