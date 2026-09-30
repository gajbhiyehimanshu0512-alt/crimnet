from langchain_ollama import OllamaLLM
from config import settings

print(f'OLLAMA_URL: {settings.ollama_url}')
print(f'OLLAMA_MODEL: {settings.ollama_model}')

try:
    # Try different URL formats
    llm = OllamaLLM(base_url='http://ollama:11434', model=settings.ollama_model)
    response = llm.invoke('Say one word')
    print(f'✓ LangChain Ollama works')
    print(f'Response: {response[:100]}')
except Exception as e:
    print(f'✗ LangChain Ollama failed: {type(e).__name__}')
    print(f'Error: {str(e)[:300]}')
