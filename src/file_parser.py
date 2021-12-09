import re
import functools
from dataclasses import dataclass
import typing

from pdfminer.layout import LAParams, LTTextLineHorizontal, LTComponent
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator

# https://stackoverflow.com/questions/22898145/how-to-extract-text-and-text-coordinates-from-a-pdf-file


LTObject = typing.Union[LTComponent, PDFPage]


@dataclass
class MatchLTTextLine:
    x1: float
    x2: float
    y1: float
    y2: float
    page: int  # page index starting at 0
    result: str


class PDFTextFinder:
    """
    Finds a specific regex within the text content of a PDF, with the coordinates
    of the discovered text.

    Note: does not search multiline.
    """

    pages: list[PDFPage]
    device: PDFPageAggregator
    interpreter: PDFPageInterpreter
    file: typing.Optional[typing.BinaryIO]

    def __init__(self, filename: str):
        self.pages, self.device, self.interpreter, self.file = self.extract_pages(
            filename
        )

    def find_matches(
        self, matching_regex: typing.Pattern[str]
    ) -> list[MatchLTTextLine]:
        assert self.file, IOError("File already closed.")

        def _page_scan(results: list[MatchLTTextLine], page_data: tuple[int, PDFPage]):
            idx, page = page_data  # unpack

            self.interpreter.process_page(page)
            layout = typing.cast(PDFPage, self.device.get_result())
            return self.traverse_hierarchy(
                layout, regex=matching_regex, depth=0, collection=results, page=idx
            )

        return functools.reduce(
            _page_scan, enumerate(self.pages), typing.cast(list[MatchLTTextLine], [])
        )

    def close(self) -> None:
        if self.file:
            self.file.close()
        self.file = None

    @staticmethod
    def extract_pages(
        filename: str,
    ) -> tuple[list[PDFPage], PDFPageAggregator, PDFPageInterpreter, typing.BinaryIO]:
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        fp = open(filename, "rb")
        pages = list(PDFPage.get_pages(fp))

        return pages, device, interpreter, fp

    @staticmethod
    def traverse_hierarchy(
        o: LTObject,
        regex: typing.Pattern[str],
        depth: int = 0,
        collection: list[MatchLTTextLine] = [],
        page: int = 0,
    ) -> list[MatchLTTextLine]:
        "Recursively traverses an object tree. Searches all text."

        if text := PDFTextFinder.get_optional_text(o):
            results = re.search(regex, text)

            if isinstance(o, LTTextLineHorizontal) and results:
                bbox: tuple[float, float, float, float] = o.bbox
                num = results.group(1)

                question_box = MatchLTTextLine(*bbox, page, num)
                collection.append(question_box)

                print(f"{PDFTextFinder.get_optional_bbox(o)} " f"{question_box.result}")

        if isinstance(o, typing.Iterable):
            o_casted = typing.cast(typing.Iterable[LTObject], o)

            for i in o_casted:
                collection = PDFTextFinder.traverse_hierarchy(
                    i, regex=regex, depth=depth + 1, collection=collection, page=page
                )
        return collection

    @staticmethod
    def get_optional_bbox(o: LTObject) -> str:
        """Bounding box of LTItem if available, otherwise empty string"""

        if hasattr(o, "bbox"):
            return "".join(f"{i:<4.0f}" for i in o.bbox)  # type: ignore
        return ""

    @staticmethod
    def get_optional_text(o: LTObject) -> str:
        """Text of LTItem if available, otherwise empty string"""

        if hasattr(o, "get_text"):
            return o.get_text().strip()  # type: ignore
        return ""
