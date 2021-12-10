import copy

from PyPDF2.pdf import PageObject

from question_splitter import Viewport

__import__("pypdf2_patch").patch()


def copy_PageObject(page: PageObject) -> PageObject:
    "Makes a shallow copy of a PageObject, ready for cropping"

    copied_page = copy.copy(page)
    for attr in {"trimBox", "mediaBox", "cropBox"}:
        existing_attr = getattr(page, attr, None)
        if existing_attr:
            setattr(copied_page, attr, copy.copy(existing_attr))
    return copied_page


def extract_viewport(
    page: PageObject,
    viewport: Viewport,
    page_size: tuple[float, float] = (595.32, 842.04),
) -> PageObject:

    new_page = PageObject.createBlankPage(width=page_size[0], height=page_size[1])  # type: ignore

    trimmed_page = copy_PageObject(page)
    trimmed_page.trimBox.lowerLeft = (0, viewport.y2)
    trimmed_page.trimBox.upperRight = (page_size[0], viewport.y1)

    new_page.mergePage(trimmed_page)

    return new_page
