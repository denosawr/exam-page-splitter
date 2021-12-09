# type: ignore

# Patch to allow merging trimmed pages
# Code taken from https://github.com/mstamy2/PyPDF2/pull/240

import PyPDF2
from PyPDF2.generic import *
from PyPDF2.pdf import ContentStream, PageObject


def _patched_mergePage(
    self: PageObject,
    page2: PageObject,
    page2transformation=None,
    ctm=None,
    expand=False,
):
    # First we work on merging the resource dictionaries.  This allows us
    # to find out what symbols in the content streams we might need to
    # rename.

    newResources = DictionaryObject()
    rename = {}
    originalResources = self["/Resources"].getObject()
    page2Resources = page2["/Resources"].getObject()
    newAnnots = ArrayObject()

    for page in (self, page2):
        if "/Annots" in page:
            annots = page["/Annots"]
            if isinstance(annots, ArrayObject):
                for ref in annots:
                    newAnnots.append(ref)

    for res in (
        "/ExtGState",
        "/Font",
        "/XObject",
        "/ColorSpace",
        "/Pattern",
        "/Shading",
        "/Properties",
    ):
        new, newrename = PageObject._mergeResources(
            originalResources, page2Resources, res
        )
        if new:
            newResources[NameObject(res)] = new
            rename.update(newrename)

    # Combine /ProcSet sets.
    newResources[NameObject("/ProcSet")] = ArrayObject(
        frozenset(originalResources.get("/ProcSet", ArrayObject()).getObject()).union(
            frozenset(page2Resources.get("/ProcSet", ArrayObject()).getObject())
        )
    )

    newContentArray = ArrayObject()

    originalContent = self.getContents()
    if originalContent is not None:
        newContentArray.append(PageObject._pushPopGS(originalContent, self.pdf))

    page2Content = page2.getContents()
    if page2Content is not None:
        page2Content = ContentStream(page2Content, self.pdf)
        page2Content.operations.insert(
            0,
            [
                map(
                    FloatObject,
                    [
                        page2.trimBox.getLowerLeft_x(),
                        page2.trimBox.getLowerLeft_y(),
                        page2.trimBox.getWidth(),
                        page2.trimBox.getHeight(),
                    ],
                ),
                "re",
            ],
        )
        page2Content.operations.insert(1, [[], "W"])
        page2Content.operations.insert(2, [[], "n"])
        if page2transformation is not None:
            page2Content = page2transformation(page2Content)
        page2Content = PageObject._contentStreamRename(page2Content, rename, self.pdf)
        page2Content = PageObject._pushPopGS(page2Content, self.pdf)
        newContentArray.append(page2Content)

    # if expanding the page to fit a new page, calculate the new media box size
    if expand:
        corners1 = [
            self.mediaBox.getLowerLeft_x().as_numeric(),
            self.mediaBox.getLowerLeft_y().as_numeric(),
            self.mediaBox.getUpperRight_x().as_numeric(),
            self.mediaBox.getUpperRight_y().as_numeric(),
        ]
        corners2 = [
            page2.mediaBox.getLowerLeft_x().as_numeric(),
            page2.mediaBox.getLowerLeft_y().as_numeric(),
            page2.mediaBox.getUpperLeft_x().as_numeric(),
            page2.mediaBox.getUpperLeft_y().as_numeric(),
            page2.mediaBox.getUpperRight_x().as_numeric(),
            page2.mediaBox.getUpperRight_y().as_numeric(),
            page2.mediaBox.getLowerRight_x().as_numeric(),
            page2.mediaBox.getLowerRight_y().as_numeric(),
        ]
        if ctm is not None:
            ctm = [float(x) for x in ctm]
            new_x = [
                ctm[0] * corners2[i] + ctm[2] * corners2[i + 1] + ctm[4]
                for i in range(0, 8, 2)
            ]
            new_y = [
                ctm[1] * corners2[i] + ctm[3] * corners2[i + 1] + ctm[5]
                for i in range(0, 8, 2)
            ]
        else:
            new_x = corners2[0:8:2]
            new_y = corners2[1:8:2]
        lowerleft = [min(new_x), min(new_y)]
        upperright = [max(new_x), max(new_y)]
        lowerleft = [min(corners1[0], lowerleft[0]), min(corners1[1], lowerleft[1])]
        upperright = [max(corners1[2], upperright[0]), max(corners1[3], upperright[1])]

        self.mediaBox.setLowerLeft(lowerleft)
        self.mediaBox.setUpperRight(upperright)

    self[NameObject("/Contents")] = ContentStream(newContentArray, self.pdf)
    self[NameObject("/Resources")] = newResources
    self[NameObject("/Annots")] = newAnnots


def patch():
    PyPDF2.pdf.PageObject._mergePage = _patched_mergePage
