from ollama import Client

try:
    client = Client(host='http://ollama:11434')
    response = client.generate(model='mistral', prompt='Hello, say one word:', stream=False)
    print('✓ Ollama direct client works')
    resp_text = response.get('response', '')[:100]
    print(f'Response: {resp_text}')
except Exception as e:
    print(f'✗ Ollama client failed: {type(e).__name__}: {str(e)[:200]}')
