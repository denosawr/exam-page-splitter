import functools
import itertools
import re
import typing
from dataclasses import dataclass

from file_parser import MatchLTTextLine, PDFTextFinder


@dataclass
class Viewport:
    y1: float
    y2: float


@dataclass
class PageData:
    page: int
    viewport: Viewport


@dataclass
class LabelMatchStore:
    question: list[MatchLTTextLine]
    next_page: list[MatchLTTextLine]
    end_of_section: list[MatchLTTextLine]
    question_continued: list[MatchLTTextLine]


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
    labels: LabelMatchStore,
    default_viewport: Viewport,
):
    current_item: MatchLTTextLine = val[0]
    next_item: typing.Optional[MatchLTTextLine] = val[1]

    if next_item:
        # check if End of Section is the next "item"
        label = filter(
            lambda x: current_item.page <= x.page and next_item.page > x.page,  # type: ignore
            labels.end_of_section,
        )

        if value := next(label, False):
            value = typing.cast(MatchLTTextLine, value)

            value.page += 1
            next_item = value

    else:  # end of paper
        next_item = labels.end_of_section[-1]
        next_item.page += 1

    question_number = int(current_item.result)

    def _determine_viewport(page: int) -> Viewport:
        label = filter(lambda x: x.page == page, labels.question_continued)  # type: ignore
        page_top = next(label, default_viewport).y1

        return Viewport(page_top, default_viewport.y2)

    pages = [
        PageData(current_item.page, Viewport(current_item.y1, default_viewport.y2))
    ] + [
        PageData(k, _determine_viewport(k))
        for k in range(current_item.page + 1, next_item.page)
    ]

    acc = {**acc, question_number: pages}

    return acc


def split_question(file: str) -> typing.Mapping[int, list[PageData]]:
    "Split a file into its component questions"

    SEARCH_FOR_QUESTION_REGEX = re.compile(r"Question (\d+)(?! con)", re.IGNORECASE)
    #                            group question number ^ |  ^ negative lookahead for "continued..."
    SEARCH_FOR_QUESTION_CONTINUED = re.compile(r"Question (\d+ con)", re.IGNORECASE)
    SEARCH_FOR_NEXT_PAGE_REGEX = re.compile(r"See (next) page", re.IGNORECASE)
    SEARCH_FOR_END_OF_SECTION = re.compile(r"End (of)(?! this booklet)", re.IGNORECASE)

    f = PDFTextFinder(file)
    labels = LabelMatchStore(
        f.find_matches(SEARCH_FOR_QUESTION_REGEX),
        f.find_matches(SEARCH_FOR_NEXT_PAGE_REGEX),
        f.find_matches(SEARCH_FOR_END_OF_SECTION),
        f.find_matches(SEARCH_FOR_QUESTION_CONTINUED),
    )
    f.close()

    TOP_OF_PAGE = max(k.y2 for k in labels.question)
    BOTTOM_OF_PAGE = min(k.y2 for k in labels.next_page) if labels.next_page else 0

    DEFAULT_VIEWPORT = Viewport(TOP_OF_PAGE + 20, BOTTOM_OF_PAGE)
    # add 20 to the default viewport in case an equation sticks out above the line

    values = functools.reduce(
        functools.partial(
            _reduce_func, labels=labels, default_viewport=DEFAULT_VIEWPORT
        ),
        iterate_with_next_item(labels.question),
        typing.cast(typing.Mapping[int, list[PageData]], {}),
    )

    return values
