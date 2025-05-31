from PyQt5.QtGui import QMovie
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QBuffer, QByteArray, QSize, QIODevice

from views.dialogs.gif_preview import GifPreviewDialog

class ClickableGifLabel(QLabel):
    def __init__(self, gif_bytes, parent=None):
        super().__init__(parent)
        self.gif_bytes = gif_bytes

        self.buffer = QBuffer()
        self.buffer.setData(QByteArray(gif_bytes))
        self.buffer.open(QIODevice.ReadOnly)

        self.movie = QMovie()
        self.movie.setDevice(self.buffer)
        self.movie.setScaledSize(QSize(300, 300))
        self.setMovie(self.movie)
        self.movie.start()

        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            preview = GifPreviewDialog(self.gif_bytes)
            preview.exec_()
