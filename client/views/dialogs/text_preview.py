from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTextEdit, QVBoxLayout, QDialog

class TextPreviewDialog(QDialog):
    def __init__(self, text: str, title: str = "Text Preview", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setText(text)
        layout.addWidget(text_edit)
        self.setLayout(layout)
        self.resize(700, 500)
