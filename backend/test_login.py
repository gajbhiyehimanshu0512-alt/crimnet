import httpx
import json

try:
    response = httpx.post(
        'http://localhost:8000/api/auth/login',
        json={'username': 'admin', 'password': 'admin123'},
        timeout=5
    )
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print(f'✓ Login successful')
        print(f'Token: {data.get("access_token", "")[:50]}...')
    else:
        print(f'✗ Login failed: {response.text[:200]}')
except Exception as e:
    print(f'✗ Error: {type(e).__name__}: {str(e)[:200]}')
