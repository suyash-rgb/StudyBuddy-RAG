import base64, zlib, urllib.request, urllib.error
src = b'graph TD\nA-->B;'
c = zlib.compressobj(9, zlib.DEFLATED, -15)
enc = base64.urlsafe_b64encode(c.compress(src) + c.flush()).decode('ascii')
req = urllib.request.Request('https://kroki.io/mermaid/svg/' + enc, headers={'User-Agent': 'Mozilla/5.0'})
try:
    print(urllib.request.urlopen(req).getcode())
except urllib.error.HTTPError as e:
    print(e.read())
