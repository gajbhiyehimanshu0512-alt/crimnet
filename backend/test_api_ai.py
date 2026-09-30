import asyncio
import httpx
import json

async def test():
    try:
        async with httpx.AsyncClient() as client:
            # Test health first
            r = await client.get('http://localhost:8000/health', timeout=5)
            print(f'Health: {r.status_code}')
            
            # Test auth login
            login_r = await client.post('http://localhost:8000/api/auth/login', 
                json={'username': 'admin', 'password': 'admin123'}, timeout=5)
            print(f'Login: {login_r.status_code}')
            
            if login_r.status_code == 200:
                token = login_r.json()['access_token']
                
                # Test AI query with token
                headers = {'Authorization': f'Bearer {token}'}
                ai_r = await client.post('http://localhost:8000/api/ai/query',
                    json={'question': 'Who are the suspects?'},
                    headers=headers, timeout=30)
                print(f'AI Query: {ai_r.status_code}')
                if ai_r.status_code == 200:
                    result = ai_r.json()
                    answer = result.get('answer', '')
                    print(f'AI Answer: {answer[:150]}')
                else:
                    print(f'AI Error: {ai_r.text[:200]}')
    except Exception as e:
        print(f'✗ Error: {type(e).__name__}: {str(e)[:200]}')

asyncio.run(test())
