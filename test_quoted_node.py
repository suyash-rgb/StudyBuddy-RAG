import urllib.request, json, base64
code='''graph TD\n"Node ID"["Node Text"] --> B'''
payload = json.dumps({'code': code, 'mermaid': {'theme': 'default'}}).encode('utf-8')
encoded = base64.urlsafe_b64encode(payload).decode('ascii').replace('=', '')
url = f'https://mermaid.ink/img/{encoded}'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    res = urllib.request.urlopen(req)
    print('Status:', res.status)
except Exception as e:
    print('Error:', e)
