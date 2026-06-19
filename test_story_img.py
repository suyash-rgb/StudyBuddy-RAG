import pymupdf
import os
from PIL import Image

Image.new('RGB', (100, 100), color='red').save('test_red.png')
html = '<img src="test_red.png"/>'
print(html)
story = pymupdf.Story(html=html, archive=pymupdf.Archive("."))
writer = pymupdf.DocumentWriter('test_story.pdf')
dev = writer.begin_page(pymupdf.paper_rect('letter'))
story.place(pymupdf.paper_rect('letter'))
story.draw(dev)
writer.end_page()
writer.close()
doc = pymupdf.open('test_story.pdf')
print('IMAGES:', doc[0].get_images())
