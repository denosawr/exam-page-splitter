def fix_click_error():
    import os

    os.environ["LC_ALL"] = "en_US.UTF-8"
    os.environ["LANG"] = "en_US.UTF-8"


fix_click_error()

import io
import typing
from pathlib import Path

import click
import PyPDF2
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import pdf_splitter
import question_splitter


def create_textbox_in_page(
    text: str, location: tuple[float, float], pagesize: tuple[float, float] = A4
) -> PyPDF2.pdf.PageObject:
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=pagesize)

    can.drawString(*location, text)
    can.save()

    packet.seek(0)

    new_pdf = PyPDF2.PdfFileReader(packet)
    text_page: PyPDF2.pdf.PageObject = new_pdf.getPage(0)

    return text_page


@click.command()
@click.argument("input")
@click.option(
    "--output",
    default=None,
    help="Folder to output to. Defaults to creating a new folder with the same name as the input file",
)
@click.option("--header", default=None, help="The header text of every processed file.")
def process_file(input: str, output: str, header: str):
    return extract_questions_from_file(input, output, header)


def extract_questions_from_file(
    input: str, output: typing.Optional[str] = None, header: typing.Optional[str] = None
):
    path = Path(input)

    # create folder
    if output:
        folder = Path(output)
        folder.mkdir(exist_ok=True)
    else:
        parent = path.parent
        folder = parent / path.stem
        folder.mkdir(exist_ok=True)

    text_page = create_textbox_in_page(header or path.stem, location=(55, 790))

    # process PDF
    results = question_splitter.split_question(input)
    input_PDF = PyPDF2.PdfFileReader(input)

    for question, pages in results.items():
        output_pdf = PyPDF2.PdfFileWriter()
        for page_data in pages:
            print(question, page_data)
            p: PyPDF2.pdf.PageObject = input_PDF.getPage(page_data.page)
            new_page = pdf_splitter.extract_viewport(p, page_data.viewport)

            new_page.mergePage(text_page)

            output_pdf.addPage(new_page)
        with open(folder / (f"{question} ({path.stem}).pdf"), "wb") as f:
            output_pdf.write(f)


if __name__ == "__main__":
    # process_file()
    # gui()
    process_file()
