# Sistema de Persistência de Conversas

## Como Funciona

O sistema agora salva automaticamente todas as conversas em arquivos JSON no diretório `conversations/`. Isso garante que o histórico não seja perdido quando o servidor reiniciar.

### Características

✅ **Persistência Automática**: Cada mensagem é salva automaticamente em JSON  
✅ **Carregamento Automático**: Conversas são restauradas na inicialização do servidor  
✅ **Leve e Rápido**: Sem dependências externas, apenas arquivos JSON  
✅ **Seguro**: Arquivos são ignorados pelo Git (não versionados)  
✅ **Debug**: Endpoints para monitorar o armazenamento  

### Estrutura dos Arquivos

```
conversations/
├── session_123.json
├── session_456.json
└── ...
```

Cada arquivo JSON contém:
```json
{
  "session_id": "session_123",
  "messages": [
    {
      "role": "user",
      "content": "Olá, como você está?",
      "message_id": "msg_001",
      "timestamp": "2024-01-01T10:00:00"
    },
    {
      "role": "assistant", 
      "content": "Oi! Tudo bem, obrigado por perguntar!",
      "message_id": "response-msg_001",
      "timestamp": "2024-01-01T10:00:01"
    }
  ],
  "metadata": {
    "conversation_id": "conv_123",
    "timezone": "America/Sao_Paulo",
    "locale": "pt-BR",
    "created_at": "2024-01-01T10:00:00",
    "last_interaction": "2024-01-01T10:01:00"
  }
}
```

### Endpoints de Debug

- `GET /debug/storage-info` - Informações sobre arquivos salvos
- `GET /debug/all-sessions` - Todas as sessões ativas
- `GET /debug/history/{session_id}` - Histórico específico

### Vantagens

1. **Simplicidade**: Sem banco de dados complexo
2. **Portabilidade**: Funciona em qualquer ambiente
3. **Backup Fácil**: Apenas copiar a pasta `conversations/`
4. **Debug Simples**: Arquivos JSON legíveis
5. **Sem Dependências**: Não precisa instalar nada novo

### Limitações

- Não é ideal para milhares de conversas simultâneas
- Não tem busca avançada
- Não tem backup automático (mas é fácil fazer manual)

### Para Produção

Se precisar escalar, pode facilmente migrar para:
- SQLite (mudança mínima no código)
- PostgreSQL/MySQL (mais robusto)
- Redis (mais rápido para cache)

Mas para desenvolvimento e uso moderado, JSON é perfeito! 🎉 