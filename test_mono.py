import pymupdf
import os

html_content = '<pre style="font-family: monospace;">HELLO WORLD</pre>'

MEDIABOX = pymupdf.paper_rect("letter")
WHERE = MEDIABOX + (36, 36, -36, -36)

story = pymupdf.Story(html=html_content, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('test_mono.pdf')
device = writer.begin_page(MEDIABOX)
story.place(WHERE)
story.draw(device)
writer.end_page()
writer.close()

doc = pymupdf.open('test_mono.pdf')
print('Text:', doc[0].get_text())
