import urllib.request
import json

url = "http://localhost:8000/api/auth/register"
payload = {
    "name": "Test User",
    "email": f"test_{int(__import__('time').time())}@example.com",
    "password": "password123",
    "role": "student"
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, method='POST')
req.add_header('Content-Type', 'application/json')

try:
    print(f"Sending request to {url}...")
    with urllib.request.urlopen(req, timeout=15) as f:
        print(f"Status Code: {f.status}")
        print(f"Response: {f.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
