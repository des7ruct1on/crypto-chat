from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

from views.dialogs.image_preview import ImagePreviewDialog

class ClickableImage(QLabel):
    def __init__(self, full_pixmap, parent=None):
        super().__init__(parent)
        self.full_pixmap = full_pixmap
        self.setPixmap(full_pixmap.scaledToWidth(300, Qt.SmoothTransformation))
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog = ImagePreviewDialog(self.full_pixmap)
            dialog.exec_()
