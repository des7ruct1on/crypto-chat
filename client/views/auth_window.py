import requests
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QTabWidget, QFormLayout, QFrame
)
from PyQt5.QtGui import QPixmap, QFont, QIcon
from PyQt5.QtCore import Qt, QSize


from services.api_client import ApiClient

class LoginWindow(QWidget):

    def __init__(self, api_client: ApiClient, on_login_success):
        super().__init__()
        self.setWindowTitle("SecureChat")
        self.setFixedSize(400, 450)  # Увеличили размер окна
        self.api_client = api_client
        self.on_login_success = on_login_success

        # Основной стиль
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                color: #e0e0e0;
                font-family: 'Segoe UI';
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #3a3a3a;
                color: #b0b0b0;
                padding: 10px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #505050;
                color: white;
            }
            QLineEdit {
                background-color: #3a3a3a;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
            QPushButton {
                background-color: #6c5ce7;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5d4aec;
            }
            QLabel {
                color: #b0b0b0;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Логотип
        logo_label = QLabel()
        pixmap = QPixmap("assets/icon.png")
        pixmap = pixmap.scaledToWidth(150, Qt.SmoothTransformation)
        logo_label.setPixmap(pixmap)
        logo_label.setAlignment(Qt.AlignCenter)

        # Заголовок
        title_label = QLabel("ServiceChat")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #6c5ce7;")

        layout.addWidget(logo_label)
        layout.addWidget(title_label)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::tab-bar {
                alignment: center;
            }
        """)

        self.login_tab = QWidget()
        self.register_tab = QWidget()

        self.tabs.addTab(self.login_tab, "Вход")
        self.tabs.addTab(self.register_tab, "Регистрация")

        self.init_login_tab()
        self.init_register_tab()

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def init_login_tab(self):
        layout = QFormLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Поля ввода
        self.login_user_id_input = QLineEdit()
        self.login_user_id_input.setPlaceholderText("Введите ваш ID")
        self.login_user_id_input.setMinimumHeight(40)

        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("Введите пароль")
        self.login_password_input.setEchoMode(QLineEdit.Password)
        self.login_password_input.setMinimumHeight(40)

        # Кнопка
        self.login_button = QPushButton("Войти")
        self.login_button.setMinimumHeight(40)
        self.login_button.setIcon(QIcon("assets/login_icon.png"))
        self.login_button.setIconSize(QSize(20, 20))
        self.login_button.clicked.connect(self.try_login)

        layout.addRow("ID пользователя:", self.login_user_id_input)
        layout.addRow("Пароль:", self.login_password_input)
        layout.addRow(self.login_button)

        self.login_tab.setLayout(layout)

    def init_register_tab(self):
        layout = QFormLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        self.register_user_id_input = QLineEdit()
        self.register_user_id_input.setPlaceholderText("Придумайте ID")
        self.register_user_id_input.setMinimumHeight(40)

        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText("Придумайте пароль")
        self.register_password_input.setEchoMode(QLineEdit.Password)
        self.register_password_input.setMinimumHeight(40)

        self.register_button = QPushButton("Зарегистрироваться")
        self.register_button.setMinimumHeight(40)
        self.register_button.setIcon(QIcon("assets/register_icon.png"))
        self.register_button.setIconSize(QSize(20, 20))
        self.register_button.clicked.connect(self.try_register)

        layout.addRow("ID пользователя:", self.register_user_id_input)
        layout.addRow("Пароль:", self.register_password_input)
        layout.addRow(self.register_button)

        self.register_tab.setLayout(layout)


    def try_login(self):
        user_id = self.login_user_id_input.text().strip()
        password = self.login_password_input.text().strip()

        if not user_id or not password:
            QMessageBox.warning(self, "Login Error", "User ID and password are required.")
            return

        if not (3 <= len(user_id) <= 50):
            QMessageBox.warning(self, "Login Error", "User ID must be between 3 and 50 characters.")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Login Error", "Password must be at least 6 characters long.")
            return

        try:
            id = self.api_client.login(user_id, password)['id']
            self.on_login_success(id)
            self.close()
        except requests.HTTPError as e:
            if e.response.status_code == 401:
                QMessageBox.warning(self, "Login Failed", "Invalid credentials.")
            else:
                QMessageBox.critical(self, "Login Error", f"Unexpected error: {e.response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Login Error", f"Unexpected error: {str(e)}")


    def try_register(self):
        user_id = self.register_user_id_input.text().strip()
        password = self.register_password_input.text().strip()

        if not user_id or not password:
            QMessageBox.warning(self, "Registration Error", "User ID and password are required.")
            return

        if not (3 <= len(user_id) <= 50):
            QMessageBox.warning(self, "Registration Error", "User ID must be between 3 and 50 characters.")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Registration Error", "Password must be at least 6 characters long.")
            return

        try:
            self.api_client.register(user_id, password)
            QMessageBox.information(self, "Registered", "Account created. You can now log in.")
            self.tabs.setCurrentIndex(0)
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                QMessageBox.warning(self, "Registration Failed", "User ID is already taken.")
            else:
                QMessageBox.critical(self, "Registration Error", f"Unexpected error: {e.response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Registration Error", f"Unexpected error: {str(e)}")
