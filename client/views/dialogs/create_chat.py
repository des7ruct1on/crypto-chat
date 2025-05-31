from PyQt5.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                             QVBoxLayout, QLabel, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from crypto.base.modes import PaddingMode, CipherMode
from utils.constants import EncryptionAlgorithm


class CreateChatDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Secure Chat")
        self.setModal(True)
        self.setFixedSize(400, 300)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("Configure Encryption Settings")
        header.setFont(QFont('Arial', 12, QFont.Bold))
        header.setStyleSheet("color: #2c3e50;")
        main_layout.addWidget(header)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet("color: #bdc3c7;")
        main_layout.addWidget(separator)

        # Form layout with modern styling
        form_layout = QFormLayout()
        form_layout.setVerticalSpacing(15)
        form_layout.setHorizontalSpacing(20)
        form_layout.setLabelAlignment(Qt.AlignLeft)

        # Algorithm selection
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.setMinimumWidth(250)
        self.algorithm_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background: white;
            }
            QComboBox::drop-down {
                width: 30px;
                border-left: 1px solid #bdc3c7;
            }
        """)
        for algo in EncryptionAlgorithm:
            self.algorithm_combo.addItem(algo.name, algo)
        form_layout.addRow("Encryption Algorithm:", self.algorithm_combo)

        # Cipher mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.setMinimumWidth(250)
        self.mode_combo.setStyleSheet(self.algorithm_combo.styleSheet())
        for mode in CipherMode:
            self.mode_combo.addItem(mode.name, mode)
        form_layout.addRow("Cipher Mode:", self.mode_combo)

        # Padding mode selection
        self.padding_combo = QComboBox()
        self.padding_combo.setMinimumWidth(250)
        self.padding_combo.setStyleSheet(self.algorithm_combo.styleSheet())
        for pad in PaddingMode:
            self.padding_combo.addItem(pad.name, pad)
        form_layout.addRow("Padding Mode:", self.padding_combo)

        main_layout.addLayout(form_layout)

        # Button box with modern styling
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("""
            QDialogButtonBox {
                margin-top: 15px;
            }
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton#okButton {
                background-color: #3498db;
                color: white;
                border: none;
            }
            QPushButton#okButton:hover {
                background-color: #2980b9;
            }
            QPushButton#cancelButton {
                background-color: #e74c3c;
                color: white;
                border: none;
            }
            QPushButton#cancelButton:hover {
                background-color: #c0392b;
            }
        """)

        # Apply custom object names for styling
        buttons.button(QDialogButtonBox.Ok).setObjectName("okButton")
        buttons.button(QDialogButtonBox.Cancel).setObjectName("cancelButton")

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def get_algorithm(self):
        return self.algorithm_combo.currentData()

    def get_mode(self):
        return self.mode_combo.currentData()

    def get_padding(self):
        return self.padding_combo.currentData()