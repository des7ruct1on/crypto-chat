import sys
import logging
import asyncio
from PyQt5.QtWidgets import QApplication, QStyleFactory
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt
from qasync import QEventLoop
from qt_material import apply_stylesheet

from services.api_client import ApiClient
from services.database_manager import Database
from views.main_window import MainWindow
from views.auth_window import LoginWindow

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger("client-app")


class ChatApplication:
    def __init__(self):
        self.api_client = ApiClient()
        self.login_window = None
        self.main_window = None
        self.app = QApplication(sys.argv)
        self.loop = QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)

        self.setup_style()

    def setup_style(self):
        """Настройка современного стиля приложения"""
        apply_stylesheet(self.app, theme='dark_cyan.xml', invert_secondary=True)

        palette = self.app.palette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(142, 45, 197).lighter())
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.app.setPalette(palette)

        # Шрифты
        font = self.app.font()
        font.setFamily("Segoe UI")
        font.setPointSize(10)
        self.app.setFont(font)

    def start_main_window(self, user_id):
        """Запуск главного окна чата"""
        if self.main_window:
            self.main_window.close()

        db_manager = Database(user_id)
        self.main_window = MainWindow(
            user_id,
            self.api_client,
            db_manager,
            on_logout=self.on_logout
        )
        self.main_window.show()

    def on_login_success(self, user_id: str):
        """Обработка успешного входа"""
        if self.login_window:
            self.login_window.close()
        self.start_main_window(user_id)

    def on_logout(self):
        """Обработка выхода из системы"""
        if self.main_window:
            self.main_window.close()
            self.main_window = None

        self.login_window = LoginWindow(
            self.api_client,
            on_login_success=self.on_login_success
        )
        self.login_window.show()

    def run(self):
        """Запуск приложения"""
        self.login_window = LoginWindow(
            self.api_client,
            on_login_success=self.on_login_success
        )
        self.login_window.show()

        with self.loop:
            self.loop.run_forever()


if __name__ == '__main__':
    chat_app = ChatApplication()
    chat_app.run()