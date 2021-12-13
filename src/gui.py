import sys
import typing
from pathlib import Path

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import main


class FileProcessThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(int)
    error_signal = QtCore.pyqtSignal(str)
    files: list[str]

    def __init__(
        self, files: list[str], callback: typing.Callable[[str], None]
    ) -> None:
        super().__init__()
        self.files = files
        self.callback = callback

    def __del__(self) -> None:
        self.wait()

    def run(self) -> None:
        try:
            for idx, file in enumerate(self.files):
                self.callback(file)

                self.progress.emit(idx)
        except Exception:
            import traceback

            exc = traceback.format_exc()
            self.error_signal.emit(exc)


class EditableList(QListWidget):
    def __init__(self, parent: typing.Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setAcceptDrops(True)
        # self.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        print("event", e.mimeData().hasUrls())
        if e.mimeData().hasUrls():
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        files = [x.toLocalFile() for x in event.mimeData().urls()]
        for f in files:
            self.addEditableItem(f)

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent) -> None:
        if e.mimeData().hasUrls():
            e.setDropAction(QtCore.Qt.CopyAction)
            e.accept()
        else:
            e.ignore()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() in {QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace}:
            self.deleteCurrentItem()

    def deleteCurrentItem(self, _clicked: typing.Optional[bool] = None) -> None:  # type: ignore
        for item in self.selectedItems():
            self.takeItem(self.row(item))

    def addEditableItem(self, name: str) -> None:
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)  # type: ignore
        self.addItem(item)


class MainWindow(QWidget):
    def __init__(self, callback: typing.Callable[[str], None]) -> None:
        super().__init__()

        self.callback = callback

        self.setWindowTitle("Exam Splitter")
        self.setAcceptDrops(True)

        title = QLabel("<h1>WACE Exam Splitter</h1>", parent=self)

        self.files_list = EditableList(self)

        # allow files list to expand to fit window size
        self.files_list.setSizePolicy(
            QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        )

        # row for list manipulation buttons
        addButton = QPushButton("+")
        addButton.clicked.connect(self.prompt_file)

        deleteButton = QPushButton("-")
        deleteButton.clicked.connect(self.files_list.deleteCurrentItem)

        addDeleteRow = QHBoxLayout()
        addDeleteRow.addWidget(
            QLabel("<i>You can drag and drop files into this window!</i>")
        )
        addDeleteRow.addStretch()
        addDeleteRow.addWidget(addButton)
        addDeleteRow.addWidget(deleteButton)

        self.progress = QProgressBar(self)

        # Row 3
        confirmRow = QHBoxLayout()

        self.progressLabel = QLabel()
        startButton = QPushButton("Start")
        closeButton = QPushButton("Close")

        startButton.clicked.connect(self.process_files)
        closeButton.clicked.connect(lambda _: sys.exit())

        confirmRow.addWidget(self.progressLabel)
        confirmRow.addStretch()
        confirmRow.addWidget(startButton)
        confirmRow.addWidget(closeButton)

        # Add all to main layout
        self.main_layout = QVBoxLayout()

        self.main_layout.addWidget(title)
        self.main_layout.addWidget(QLabel("Files to process:"))
        self.main_layout.addWidget(self.files_list)

        self.main_layout.addLayout(addDeleteRow)
        self.main_layout.addWidget(self.progress)
        self.main_layout.addLayout(confirmRow)
        # self.main_layout.addStretch()

        self.setLayout(self.main_layout)

    def prompt_file(self, _checked: bool) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add PDF files", "", "PDF documents (*.pdf)"
        )
        print(files)
        for file in files:
            self.files_list.addEditableItem(file)

    def process_files(self, _checked: bool) -> None:
        self.progressLabel.setText("Starting...")
        self.files_to_progress = [
            self.files_list.item(i).text() for i in range(self.files_list.count())
        ]
        self.process_thread = FileProcessThread(self.files_to_progress, self.callback)

        self.process_thread.progress.connect(self.update_progress_bar)
        self.process_thread.error_signal.connect(self.display_error_dialog)
        self.process_thread.start()
        self.update_progress_bar(-1)

    def update_progress_bar(self, progress_idx: int) -> None:
        self.progress.setValue(
            int((progress_idx + 1) / len(self.files_to_progress) * 100)
        )

        try:
            next_file = self.files_to_progress[progress_idx + 1]
            self.progressLabel.setText(
                f"> {Path(next_file).stem} ({progress_idx+1}/{len(self.files_to_progress)})"
            )
        except IndexError:
            self.progress.setValue(100)
            self.progressLabel.setText("Done")

    def display_error_dialog(self, err: str) -> None:
        msg = QMessageBox()

        msg.setIcon(QMessageBox.Critical)
        msg.setText("An error occurred...")
        msg.setInformativeText(err)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.buttonClicked.connect(sys.exit)  # type: ignore

        msg.exec_()


def _main(callback: typing.Callable[[str], None]):
    app = QApplication(sys.argv)

    window = MainWindow(callback)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    _main(main.extract_questions_from_file)
