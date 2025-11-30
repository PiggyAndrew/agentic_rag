import requests
import json

url = "http://localhost:8000/chat"
data = {
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}

print(f"Sending request to {url} with data: {data}")
try:
    with requests.post(url, json=data, stream=True) as response:
        print(f"Response status code: {response.status_code}")
        print("Response content:")
        for line in response.iter_lines():
            if line:
                print(line.decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
