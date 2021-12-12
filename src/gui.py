import sys
import threading
from pathlib import Path

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import *


class FileProcessThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(int)
    error_signal = QtCore.pyqtSignal(str)
    files: list[str]

    def __init__(self, files: list[str], callback):
        super().__init__()
        self.files = files
        self.callback = callback

    def __del__(self):
        self.wait()

    def run(self):
        try:
            for idx, file in enumerate(self.files):
                self.callback(file)

                self.progress.emit(idx)
        except Exception:
            import traceback

            exc = traceback.format_exc()
            self.error_signal.emit(exc)


class EditableList(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAcceptDrops(True)
        # self.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)

    def dragEnterEvent(self, event):
        print("event", event.mimeData().hasUrls())
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        print("drop")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            self.addEditableItem(f)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() in {QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace}:
            self.deleteCurrentItem()

    def deleteCurrentItem(self, *args, **kwargs) -> None:
        for item in self.selectedItems():
            self.takeItem(self.row(item))

    def addEditableItem(self, name):
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        self.addItem(item)


class MainWindow(QWidget):
    def __init__(self, callback):
        super().__init__()

        self.callback = callback

        self.setWindowTitle("Exam Splitter")
        self.setAcceptDrops(True)

        self.main_layout = QVBoxLayout()

        title = QLabel("<h1>WACE Exam Splitter</h1>", parent=self)

        self.files_list = EditableList(self)
        # allow files list to expand
        self.files_list.setSizePolicy(
            QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        )

        self.main_layout.addWidget(title)
        self.main_layout.addWidget(QLabel("Files to process:"))
        self.main_layout.addWidget(self.files_list)

        addDeleteRow = QHBoxLayout()
        addButton = QPushButton("+")
        addButton.clicked.connect(self.prompt_file)

        deleteButton = QPushButton("-")
        deleteButton.clicked.connect(self.files_list.deleteCurrentItem)

        addDeleteRow.addWidget(
            QLabel("<i>You can drag and drop files into this window!</i>")
        )
        addDeleteRow.addStretch()
        addDeleteRow.addWidget(addButton)
        addDeleteRow.addWidget(deleteButton)

        self.main_layout.addLayout(addDeleteRow)

        self.progress = QProgressBar(self)
        self.main_layout.addWidget(self.progress)

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

        self.main_layout.addLayout(confirmRow)
        # self.main_layout.addStretch()

        self.setLayout(self.main_layout)

    def prompt_file(self, event):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add PDF files", "", "PDF documents (*.pdf)"
        )
        print(files)
        for file in files:
            self.files_list.addEditableItem(file)

    def process_files(self, event):
        self.progressLabel.setText("Starting...")
        self.files_to_progress = [
            self.files_list.item(i).text() for i in range(self.files_list.count())
        ]
        self.process_thread = FileProcessThread(self.files_to_progress, self.callback)

        self.process_thread.progress.connect(self.update_progress_bar)
        self.process_thread.error_signal.connect(self.display_error_dialog)
        self.process_thread.start()
        self.update_progress_bar(-1)

    def update_progress_bar(self, progress_idx: int):
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

    def display_error_dialog(self, err: str):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("An error occurred...")
        msg.setInformativeText(err)
        msg.setWindowTitle("Error")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.buttonClicked.connect(sys.exit)

        msg.exec_()


def main(callback):
    app = QApplication(sys.argv)

    window = MainWindow(callback)

    window.show()
    sys.exit(app.exec_())
