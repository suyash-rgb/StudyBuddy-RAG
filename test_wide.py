import pymupdf
import os

pix = pymupdf.Pixmap(pymupdf.csRGB, 1000, 300, 0)
pix.clear_with(255,0,0)
pix.save('wide.png')

html_content = '<img src="wide.png" width="1000" height="300" />'

MEDIABOX = pymupdf.paper_rect("letter")
WHERE = MEDIABOX + (36, 36, -36, -36)

story = pymupdf.Story(html=html_content, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('wide.pdf')
device = writer.begin_page(MEDIABOX)
story.place(WHERE)
story.draw(device)
writer.end_page()
writer.close()

doc = pymupdf.open('wide.pdf')
if len(doc) > 0 and len(doc[0].get_image_info()) > 0:
    print('Bbox:', doc[0].get_image_info()[0]['bbox'])
else:
    print('No image found in PDF')
