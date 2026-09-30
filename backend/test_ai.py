import asyncio
import sys
sys.path.insert(0, '/app')
from ai.rag_engine import RAGEngine

async def test():
    engine = RAGEngine()
    try:
        result = await engine.answer('Who are the top suspects?')
        print('✓ AI Query successful')
        print(f'Answer: {result.get("answer", "N/A")[:150]}')
    except Exception as e:
        print(f'✗ AI Query failed: {type(e).__name__}: {str(e)[:300]}')

asyncio.run(test())
