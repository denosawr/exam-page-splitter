import re
import functools
from dataclasses import dataclass
from typing import Iterable, Any, BinaryIO, Union, Pattern, cast, Generator

from pdfminer.layout import LAParams, LTTextBox, LTTextLineHorizontal, LTComponent
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator


@dataclass
class MatchLTTextLine:
    x1: float
    x2: float
    y1: float
    y2: float
    page: int  # page index starting at 0
    question: int


class PDFTextFinder:
    """
    Finds a specific regex within the text content of a PDF, with the coordinates
    of the discovered text.

    Note: does not search multiline.
    """

    pages: list[PDFPage]

    def __init__(self, filename: str):
        self.pages, self.device, self.interpreter, self.file = self.extract_pages(
            filename
        )

    def find_matches(self, matching_regex: Pattern):
        assert self.file, IOError("File already closed.")

        def _page_scan(results, page_data):
            idx, page = page_data  # unpack

            self.interpreter.process_page(page)
            layout = cast(PDFPage, self.device.get_result())
            return self.traverse_hierarchy(
                layout, regex=matching_regex, depth=0, collection=results, page=idx
            )

        return functools.reduce(_page_scan, enumerate(self.pages), [])

    def close(self) -> None:
        if self.file:
            self.file.close()
        self.file = None

    @staticmethod
    def extract_pages(
        filename: str,
    ) -> tuple[
        Generator[PDFPage, None, None], PDFPageAggregator, PDFPageInterpreter, BinaryIO
    ]:
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        fp = open(filename, "rb")
        pages = PDFPage.get_pages(fp)
        fp.close()

        return pages, device, interpreter, fp

    @staticmethod
    def traverse_hierarchy(
        o: Union[LTComponent, PDFPage],
        regex: Pattern,
        depth: int = 0,
        collection: list[MatchLTTextLine] = [],
        page: int = 0,
    ) -> list[MatchLTTextLine]:
        "Recursively traverses an object tree. Searches all text."

        if text := PDFTextFinder.get_optional_text(o):
            results = re.search(regex, text)

            if isinstance(o, LTTextLineHorizontal) and results:
                bbox: tuple[float, float, float, float] = o.bbox
                num = int(results.group(1))  # regex acts as typeguard

                question_box = MatchLTTextLine(*bbox, page, num)
                collection.append(question_box)

                print(
                    f"{PDFTextFinder.get_optional_bbox(o)} " f"{question_box.question}"
                )

        if isinstance(o, Iterable):
            for i in o:
                collection = PDFTextFinder.traverse_hierarchy(
                    i, regex=regex, depth=depth + 1, collection=collection, page=page
                )
        return collection

    @staticmethod
    def get_optional_bbox(o: LTComponent) -> str:
        """Bounding box of LTItem if available, otherwise empty string"""
        if hasattr(o, "bbox"):
            return "".join(f"{i:<4.0f}" for i in o.bbox)
        return ""

    @staticmethod
    def get_optional_text(o: LTComponent) -> str:
        """Text of LTItem if available, otherwise empty string"""
        if hasattr(o, "get_text"):
            return o.get_text().strip()
        return ""
