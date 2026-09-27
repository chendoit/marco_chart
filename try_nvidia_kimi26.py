
import requests, base64

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
stream = True

def read_b64(path):
  with open(path, "rb") as f:
    return base64.b64encode(f.read()).decode()

headers = {
  "Authorization": "Bearer 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",
  "Accept": "text/event-stream" if stream else "application/json"
}
#
# payload = {
#   "model": "moonshotai/kimi-k2.6",
#   "messages": [{"role":"user","content":"hi how are you"}],
#   "max_tokens": 16384,
#   "temperature": 1.00,
#   "top_p": 1.00,
#   "stream": stream,
#   "chat_template_kwargs": {"thinking":False},
# }
#
# response = requests.post(invoke_url, headers=headers, json=payload, stream=stream)
# if stream:
#     for line in response.iter_lines():
#         if line:
#             print(line.decode("utf-8"))
# else:
#     print(response.json())
payload = {
    "model": "moonshotai/kimi-k2.6",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 32,
    "temperature": 0,
    "top_p": 1,
    "stream": False,
}

r = requests.post(invoke_url, headers=headers, json=payload, timeout=30)

print("status:", r.status_code)
print(r.text[:1000])