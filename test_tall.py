import pymupdf
import os

pix = pymupdf.Pixmap(pymupdf.csRGB, 400, 900, 0)
pix.clear_with(255,0,0)
pix.save('tall.png')

html_content = '<img src="tall.png" width="400" height="900" />'

MEDIABOX = pymupdf.paper_rect("letter")
WHERE = MEDIABOX + (36, 36, -36, -36)

story = pymupdf.Story(html=html_content, archive=pymupdf.Archive(os.getcwd()))
writer = pymupdf.DocumentWriter('tall_pdf.pdf')

more = 1
while more:
    device = writer.begin_page(MEDIABOX)
    more, _ = story.place(WHERE)
    story.draw(device)
    writer.end_page()

writer.close()
doc = pymupdf.open('tall_pdf.pdf')
print('Pages:', len(doc))
for i in range(len(doc)):
    print(f'Page {i} images:', len(doc[i].get_image_info()))
