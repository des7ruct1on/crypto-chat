from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QDialog
from PyQt5.QtCore import Qt, QBuffer, QByteArray, QSize, QIODevice

class GifPreviewDialog(QDialog):
    def __init__(self, gif_bytes, parent=None):
        super().__init__(parent)
        self.setWindowTitle("gif preview")
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_DeleteOnClose)

        label = QLabel()

        self.buffer = QBuffer()
        self.buffer.setData(QByteArray(gif_bytes))
        self.buffer.open(QIODevice.ReadOnly)

        self.movie = QMovie()
        self.movie.setDevice(self.buffer)
        self.movie.setScaledSize(QSize(600, 600))

        label.setMovie(self.movie)
        self.movie.start()

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        self.resize(600, 600)
