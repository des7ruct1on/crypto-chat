from PyQt5.QtWidgets import QLabel, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt

class ImagePreviewDialog(QDialog):
    def __init__(self, pixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image preview")
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_DeleteOnClose)

        label = QLabel()
        label.setPixmap(pixmap.scaled(800, 800, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        self.setLayout(layout)
        self.resize(label.pixmap().size())
