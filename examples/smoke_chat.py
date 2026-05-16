import json
from urllib.request import Request, urlopen

payload = {
    "messages": [
        {
            "role": "user",
            "content": "Hiring a mid-level Java developer who works with stakeholders. Add personality too.",
        }
    ]
}

request = Request(
    "http://127.0.0.1:8000/chat",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

with urlopen(request, timeout=30) as response:
    print(response.read().decode("utf-8"))
