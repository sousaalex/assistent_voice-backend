import os
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from textwrap import dedent
from openai import AzureOpenAI
from dotenv import load_dotenv
from .prompt.prompt import system_prompt
load_dotenv()

endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = "2025-04-01-preview" 
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_ID")
api_key = os.getenv("AZURE_OPENAI_API_KEY")

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version=api_version
)

def search_web_duckduckgo(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    
    url = 'https://html.duckduckgo.com/html/'
    params = {'q': query}
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.post(url, data=params, headers=headers, timeout=10)
    response.raise_for_status()  # Levanta erro em caso de status != 200
    
    soup = BeautifulSoup(response.text, 'html.parser')
    resultados = []
    
    blocos = soup.find_all('div', class_='result')
    
    for bloco in blocos:
        link_tag = bloco.find('a', class_='result__a')
        if not link_tag:
            continue
        
        titulo = link_tag.get_text(strip=True)
        link = link_tag['href']
        
        resultados.append({'titulo': titulo, 'link': link})
        
        if len(resultados) >= max_results:
            break
    
    return resultados

def extrair_conteudo_pagina(url: str) -> str:
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'form', 'nav']):
            tag.decompose()
        
        texto = soup.get_text(separator='\n')
        texto_limpo = '\n'.join([linha.strip() for linha in texto.splitlines() if linha.strip()])
        return texto_limpo
    
    except Exception as e:
        return f"[ERRO AO ACEDER]: {e}"

tools_config = [
    {
        "type": "function",
        "function": {
            "name": "search_web_duckduckgo",
            "description": "Pesquisa informações na web usando DuckDuckGo. Ideal para buscar dados atuais, notícias, definições, e informações gerais.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo ou pergunta para pesquisar na web."},
                    "max_results": {"type": "integer", "description": "Número máximo de resultados (padrão: 5, máximo: 10)"}
                },
                "required": ["query"]
            }
        }
    }
]

tools_functions = {
    "search_web_duckduckgo": search_web_duckduckgo
}

class LLM:
    def __init__(self, client, tools_config, tools_functions):
        self.client = client
        self.tools_config = tools_config
        self.tools_functions = tools_functions

    def run(self, messages):
        response = self.client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            tools=self.tools_config,
            tool_choice="auto"
        )

        message = response.choices[0].message

        if message.tool_calls:
            # Adiciona a resposta do assistente com as tool_calls
            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls
            })
            
            # Executa cada tool_call
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                if func_name in self.tools_functions:
                    try:
                        args = json.loads(tool_call.function.arguments)
                        result = self.tools_functions[func_name](**args)
                        
                        # Adiciona o resultado da ferramenta
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=False)
                        })
                    except Exception as e:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({"erro": f"Erro ao executar {func_name}: {str(e)}"}, ensure_ascii=False)
                        })
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({"erro": f"Ferramenta desconhecida: {func_name}"}, ensure_ascii=False)
                    })
            
            # Chama novamente para obter a resposta final
            return self.run(messages)
        else:
            return message.content

def get_unified_system_prompt() -> str:
    system = system_prompt()
    return dedent(system).strip()

def main():
    llm = LLM(client, tools_config, tools_functions)
    system_prompt_text = get_unified_system_prompt()
    messages = [
        {
            "role": "system",
            "content": system_prompt_text
        },
        {
            "role": "user",
            "content": "Pesquisa sobre as últimas notícias de inteligência artificial"
        }
    ]

    result = llm.run(messages)
    print("\nResultado:")
    print(result)

if __name__ == "__main__":
    main()
