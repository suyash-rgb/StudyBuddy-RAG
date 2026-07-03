import pymupdf
import os
import urllib.request

req = urllib.request.Request('https://mermaid.ink/img/pYxBCsMwEAS_Iuuc_EBfINBLbz2oR0lsRQK5i7KDDbn7rpwQCLqwzAy7A2v1oB3s2G6A4mBscH1m3mB8Eiw2e4u_8k_W0rZ0y52m6V4nOQ_m7j1Z1LqUq5wWz8s_R25-u1_cW6_u2sVv', headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as res, open('test_jpeg_as_png.png', 'wb') as f:
    f.write(res.read())

html_content = '<img src="test_jpeg_as_png.png" />'
MEDIABOX = pymupdf.paper_rect("letter")
WHERE = MEDIABOX + (36, 36, -36, -36)

story = pymupdf.Story(html=html_content, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('test_jpeg.pdf')
device = writer.begin_page(MEDIABOX)
story.place(WHERE)
story.draw(device)
writer.end_page()
writer.close()

doc = pymupdf.open('test_jpeg.pdf')
print('Image Info:', doc[0].get_image_info())
