import io
import sys
from io import StringIO
from pathlib import Path
from pprint import pprint

import PyPDF2
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import question_splitter

# convert to command-line (click) later
file = sys.argv[1]
path = Path(file)

results = question_splitter.split_question(file)

pprint(results)

import pdf_splitter

src_f = open(file, "rb")
input_PDF = PyPDF2.PdfFileReader(file)

parent = path.parent
folder = parent / path.stem
folder.mkdir(exist_ok=True)

packet = io.BytesIO()
print(A4)
can = canvas.Canvas(packet, pagesize=A4)
can.drawString(55, 790, path.stem)
can.save()

packet.seek(0)

new_pdf = PyPDF2.PdfFileReader(packet)
textPage: PyPDF2.pdf.PageObject = new_pdf.getPage(0)

for question, pages in results.items():
    output = PyPDF2.PdfFileWriter()
    for page_data in pages:
        print(question, page_data)
        p: PyPDF2.pdf.PageObject = input_PDF.getPage(page_data.page)
        new_page = pdf_splitter.extract_viewport(p, page_data.viewport)

        new_page.mergePage(textPage)

        output.addPage(new_page)
    with open(folder / (str(question) + ".pdf"), "wb") as f:
        output.write(f)

src_f.close()
