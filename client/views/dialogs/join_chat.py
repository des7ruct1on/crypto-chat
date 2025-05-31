from PyQt5.QtWidgets import (QLineEdit, QDialog, QDialogButtonBox, QFormLayout)

class JoinChatDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Join Existing Chat")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)

        self.chat_id_input = QLineEdit()
        self.chat_id_input.setPlaceholderText("Enter the Chat ID provided by the creator")
        layout.addRow("Chat ID:", self.chat_id_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addRow(buttons)
        self.setLayout(layout)

    def get_chat_id(self):
        return self.chat_id_input.text().strip()
