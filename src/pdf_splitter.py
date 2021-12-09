import copy
import math
import sys
import typing

import PyPDF2
from PyPDF2.pdf import PageObject

"""
Reverse imposing:
--A3--         --A4--
[12| 1]         [1]
[ 2|11]         [2]
[10| 3]    =>   [3]
  ...           ...
[ 6| 7]         [6]
                [7]
                ...
               [12]
"""

__import__("pypdf2_patch").patch()


def copy_PageObject(page: PageObject) -> PageObject:
    "Makes a shallow copy of a PageObject, ready for cropping"

    copied_page = copy.copy(page)
    for attr in {"trimBox", "mediaBox", "cropBox"}:
        copied_page[attr] = copy.copy(page[attr])  # type: ignore
    return copied_page


def split_pages(src: str, dst: str) -> None:
    src_f = open(src, "rb")
    dst_f = open(dst, "wb")

    input_PDF = PyPDF2.PdfFileReader(src_f)
    num_pages: int = input_PDF.getNumPages()

    first_half: list[PageObject] = []
    second_half: list[PageObject] = []

    for i in range(num_pages):
        p: PageObject = input_PDF.getPage(i)
        q = copy_PageObject(p)
        print(q.mediaBox)

        x1, x2 = typing.cast(tuple[float, float], p.mediaBox.lowerLeft)
        x3, x4 = typing.cast(tuple[float, float], p.mediaBox.upperRight)

        x1, x2 = math.floor(x1), math.floor(x2)
        x3, x4 = math.floor(x3), math.floor(x4)
        x5, x6 = math.floor(x3 / 2), math.floor(x4 / 2)

        if x3 > x4:
            # horizontal
            p.trimBox.upperRight = (x5, x4)
            p.trimBox.lowerLeft = (x1, x2)

            q.trimBox.upperRight = (x3, x4)
            q.trimBox.lowerLeft = (x5, x2)
        else:
            # vertical
            p.trimBox.upperRight = (x3, x4)
            p.trimBox.lowerLeft = (x1, x6)

            q.trimBox.upperRight = (x3, x6)
            q.trimBox.lowerLeft = (x1, x2)

        if i in range(1, num_pages + 1, 2):
            first_half += [p]
            second_half += [q]
        else:
            first_half += [q]
            second_half += [p]

    output = PyPDF2.PdfFileWriter()
    for page in first_half + second_half[::-1]:
        # output.addPage(page)
        blank_page = PageObject.createBlankPage(
            width=595.32, height=842.04
        )  # type:ignore

        # newPage = output.addBlankPage(595.32, 842.04)  # A4 size
        blank_page.mergePage(page)
        output.addPage(blank_page)

    output.write(dst_f)
    src_f.close()
    dst_f.close()


if len(sys.argv) < 3:
    print("\nusage:\n$ python reverse_impose.py input.pdf output.pdf")
    sys.exit()

input_file = sys.argv[1]
output_file = sys.argv[2]

print("Hello", sys.argv)
split_pages(input_file, output_file)
