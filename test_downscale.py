import urllib.request
import json
import base64
import pymupdf
import os

code='''graph LR
A[Requirement Gathering] --> B[Requirement Analysis] --> C[Feasibility Study]
D[Design] --> E[Implementation] --> F[Testing]'''

payload = json.dumps({'code': code, 'mermaid': {'theme': 'default'}}).encode('utf-8')
encoded = base64.urlsafe_b64encode(payload).decode('ascii').replace('=', '')
url = f'https://mermaid.ink/img/{encoded}'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

with urllib.request.urlopen(req) as res:
    data = res.read()

with open('downscale.jpg', 'wb') as f:
    f.write(data)

html = '<img src="downscale.jpg" width="500" height="150" />'
story = pymupdf.Story(html=html, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('downscale.pdf')
story.place(pymupdf.paper_rect('letter')+(36,36,-36,-36))
story.draw(writer.begin_page(pymupdf.paper_rect('letter')))
writer.end_page()
writer.close()
