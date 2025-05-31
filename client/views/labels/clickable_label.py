from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt

class ClickableLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._click_handler = None

    def set_click_handler(self, handler):
        self._click_handler = handler
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if self._click_handler:
            self._click_handler(event)
