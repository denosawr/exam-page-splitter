# import pdfrw
from dataclasses import dataclass
import functools
import sys
import typing
import itertools

from file_parser import PDFTextFinder, MatchLTTextLine


@dataclass
class Viewport:
    y1: float
    y2: float


# convert to command-line (click) later
file = sys.argv[1]

import re

# for page in pages:
#     print(page)
#     sys.exit()

SEARCH_FOR_QUESTION_REGEX = re.compile(r"Question (\d+)(?! con)", re.IGNORECASE)
#                            group question number ^ |  ^ negative lookahead for "continued..."
SEARCH_FOR_QUESTION_CONTINUED = re.compile(r"Question (\d+ con)", re.IGNORECASE)
SEARCH_FOR_NEXT_PAGE_REGEX = re.compile(r"See (next) page", re.IGNORECASE)
SEARCH_FOR_END_OF_SECTION = re.compile(r"End (of)(?! this booklet)", re.IGNORECASE)


print("x1  y1  x2  y2   text")
from pprint import pprint

pprint

f = PDFTextFinder(file)
question_labels = f.find_matches(SEARCH_FOR_QUESTION_REGEX)
next_page_labels = f.find_matches(SEARCH_FOR_NEXT_PAGE_REGEX)
end_of_section_labels = f.find_matches(SEARCH_FOR_END_OF_SECTION)
question_continued_labels = f.find_matches(SEARCH_FOR_QUESTION_CONTINUED)
f.close()

TOP_OF_PAGE = max(k.y2 for k in question_labels)
BOTTOM_OF_PAGE = min(k.y2 for k in next_page_labels) if next_page_labels else 0
DEFAULT_VIEWPORT = Viewport(TOP_OF_PAGE, BOTTOM_OF_PAGE)


@dataclass
class PageData:
    page: int
    viewport: Viewport


T = typing.TypeVar("T")


def iterate_with_next_item(
    some_iterable: typing.Iterable[T],
) -> typing.Iterable[tuple[T, typing.Optional[T]]]:
    items, nexts = itertools.tee(some_iterable, 2)
    nexts = itertools.chain(itertools.islice(nexts, 1, None), [None])
    return zip(items, nexts)


def _reduce_func(
    acc: typing.Mapping[int, list[PageData]],
    val: tuple[MatchLTTextLine, typing.Optional[MatchLTTextLine]],
):
    current_item: MatchLTTextLine = val[0]
    next_item: typing.Optional[MatchLTTextLine] = val[1]

    if next_item:
        # check if End of Section is the next "item"
        label = filter(
            lambda x: current_item.page <= x.page and next_item.page > x.page,  # type: ignore
            end_of_section_labels,
        )

        if value := next(label, False):
            value = typing.cast(MatchLTTextLine, value)

            value.page += 1
            next_item = value

    else:  # end of paper
        next_item = end_of_section_labels[-1]
        next_item.page += 1

    question_number = int(current_item.result)

    def _determine_viewport(page: int) -> Viewport:
        label = filter(lambda x: x.page == page, question_continued_labels)  # type: ignore
        page_top = next(label, DEFAULT_VIEWPORT).y1

        return Viewport(page_top, DEFAULT_VIEWPORT.y2)

    pages = [PageData(current_item.page, Viewport(current_item.y1, BOTTOM_OF_PAGE))] + [
        PageData(k, _determine_viewport(k))
        for k in range(current_item.page + 1, next_item.page)
    ]

    acc = {**acc, question_number: pages}

    return acc


values = functools.reduce(
    _reduce_func,
    iterate_with_next_item(question_labels),
    typing.cast(typing.Mapping[int, list[PageData]], {}),
)

pprint(values)
