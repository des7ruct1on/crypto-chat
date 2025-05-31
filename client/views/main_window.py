import os
import uuid
import base64
import logging
import asyncio
import requests
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QTabWidget, QTabBar,
                             QFileDialog, QListWidget, QMessageBox, QSplitter,
                             QDialog, QMenu, QStatusBar)
from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QThread
from PyQt5.QtGui import QIcon, QGuiApplication
from PyQt5.QtWidgets import QPushButton, QStyle

from messaging.kafka.consumer import KafkaEventConsumer
from crypto.diffie_hellman.diffie_hellman import DiffieHellman
from crypto.base.key import derive_cipher_key_16
from views.dialogs.create_chat import CreateChatDialog
from views.dialogs.join_chat import JoinChatDialog
from views.widgets.chat_tab import ChatTab
from services.api_client import ApiClient
from services.database_manager import Database
from utils.cryptography_manager import CryptographyManager
from utils.workers.decryption_worker import DecryptionWorker
from utils.workers.encryption_worker import EncryptionWorker
from utils.workers.kafka_worker import KafkaWorker
from utils.constants import EncryptionAlgorithm

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SecureChat")


class MainWindow(QMainWindow):

    def __init__(self, user_id, api_client: ApiClient, db_manager: Database, on_logout=None):
        super().__init__()
        self.setWindowTitle("ServiceChat")
        self.resize(800, 600)

        # Установка светло-зеленого стиля
        self.setStyleSheet("""
            QMainWindow {
                background-color: #e8f5e9;
            }
            QPushButton {
                background-color: #e8f5e9;
                border: 1px solid #81c784;
                padding: 5px;
                border-radius: 3px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #a5d6a7;
            }
            QListWidget {
                background-color: grey;
                border: 1px solid #81c784;
            }
            QTabWidget::pane {
                border: 1px solid #81c784;
                background: white;
            }
            QTabBar::tab {
                background: #c8e6c9;
                border: 1px solid #81c784;
                padding: 5px;
            }
            QTabBar::tab:selected {
                background: #a5d6a7;
            }
            QLabel {
                color: #2e7d32;
            }
            QStatusBar {
                background-color: #c8e6c9;
                color: #2e7d32;
            }
        """)

        self.user_id = user_id
        logger.info(f"Client User ID: {self.user_id}")
        self.current_chat_id = None
        self.on_logout = on_logout

        api_base_url = os.environ.get("CHAT_API_URL", "http://localhost:8000")

        self.api_client = api_client
        self.kafka_thread = QThread()
        self.kafka_worker = KafkaWorker(
            kafka_consumer=KafkaEventConsumer(
                bootstrap_servers="localhost:29092",
                topics=["chat_messages"],
                group_id=self.user_id
            )
        )

        self.kafka_worker.moveToThread(self.kafka_thread)
        self.kafka_thread.started.connect(self.kafka_worker.start)
        self.kafka_worker.message_received.connect(self.kafka_producer_callback)
        self.kafka_thread.start()
        self.crypto_manager = CryptographyManager()
        self.db_manager = db_manager

        self.encryption_worker: Optional[EncryptionWorker] = None
        self.decryption_worker: Optional[DecryptionWorker] = None
        self._pending_decryption_files: Dict[str, Path] = {}

        self.chat_keys: Dict[str, bytes] = {}

        self.init_ui()

        self.chats_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chats_list.customContextMenuRequested.connect(self.show_chat_context_menu)

        QTimer.singleShot(0, self.run_async_init)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.user_id_label = QLabel(f"Your User ID: {self.user_id}")
        self.user_id_label.setCursor(Qt.PointingHandCursor)
        self.user_id_label.setToolTip("Click to copy your User ID")
        self.user_id_label.mousePressEvent = self.copy_user_id_to_clipboard

        self.status_bar.addPermanentWidget(self.user_id_label)

    def copy_user_id_to_clipboard(self, event):
        QGuiApplication.clipboard().setText(self.user_id)
        self.statusBar().showMessage("User ID copied to clipboard", 2000)

    def run_async_init(self):
        asyncio.create_task(self.async_init())

    async def async_init(self):
        self.load_chats()

    def kafka_producer_callback(self, data):
        msg_type = data.get("type")
        chat_id = data.get("chat_id", None)

        chats = self.db_manager.get_chats()
        exists = any(chat["chat_id"] == chat_id for chat in chats)
        if not exists:
            return

        if msg_type == "user_left":
            logger.info(f"User {data.get('user_id')} left chat {chat_id}")
            self.on_user_left({
                'chat_id': chat_id,
                'user_id': data['user_id']
            })
        elif msg_type == "encryption_ready":
            logger.info(f"Encryption ready for chat {chat_id}")
            self.on_encryption_ready(chat_id)
        elif msg_type == "chat_closed":
            logger.info(f"Chat {chat_id} closed by server/creator.")
            self.on_chat_closed_by_server(chat_id)

        msg_data = data.get("data", {})
        recipient_id = msg_data.get("recipient")
        chat_id = msg_data.get("chat_id")

        if recipient_id != self.user_id:
            return

        if msg_type == "message":
            logger.debug(f"Received message for chat {chat_id}")
            self.handle_incoming_message(msg_data)
        if msg_type == "file":
            logger.debug(f"Received file metadata for chat {chat_id}")
            self.handle_incoming_file(msg_data)

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QHBoxLayout(self.central_widget)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(250)

        self.chats_list = QListWidget()
        self.chats_list.itemDoubleClicked.connect(self.on_chat_selected)

        # Измененное расположение кнопок - вертикально
        chat_buttons_layout = QVBoxLayout()
        self.create_chat_button = QPushButton("New Chat")
        self.create_chat_button.clicked.connect(self.create_chat_dialog)
        self.join_chat_button = QPushButton("Join Chat")
        self.join_chat_button.clicked.connect(self.join_chat_dialog)

        chat_buttons_layout.addWidget(self.create_chat_button)
        chat_buttons_layout.addWidget(self.join_chat_button)
        chat_buttons_layout.setSpacing(5)  # Уменьшаем расстояние между кнопками

        left_layout.addWidget(QLabel("Your Chats:"))
        left_layout.addWidget(self.chats_list)
        left_layout.addLayout(chat_buttons_layout)

        self.logout_button = QPushButton("Logout")
        self.logout_button.clicked.connect(self.logout)
        left_layout.addWidget(self.logout_button, alignment=Qt.AlignBottom)

        self.chat_tabs = QTabWidget()
        self.chat_tabs.setTabsClosable(True)
        self.chat_tabs.tabCloseRequested.connect(self.close_chat_tab)
        self.chat_tabs.currentChanged.connect(self.on_tab_changed)

        self.no_chat_widget = QLabel("<h2>Select or create a chat</h2>")
        self.no_chat_widget.setAlignment(Qt.AlignCenter)
        self.chat_tabs.addTab(self.no_chat_widget, "")
        self.chat_tabs.setTabEnabled(0, False)
        self.chat_tabs.tabBar().setVisible(False)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.chat_tabs)
        splitter.setSizes([200, 600])

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def logout(self):
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to log out?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if self.on_logout:
                self.on_logout()

    def get_current_chat_tab(self) -> Optional[ChatTab]:
        current_widget = self.chat_tabs.currentWidget()
        if isinstance(current_widget, ChatTab):
            return current_widget
        return None

    def load_chats(self):
        self.chats_list.clear()
        try:
            chats = self.db_manager.get_chats()
            if not chats:
                logger.info("No existing chats found in the database.")
                return

            logger.info(f"Loading {len(chats)} chats from database.")
            for chat in chats:
                status_indicator = f" [{chat.get('status', 'unknown')}]"
                list_item_text = f"{chat['chat_id'][:8]}... ({chat['algorithm']}){status_indicator}"
                self.chats_list.addItem(list_item_text)
                self.chats_list.item(self.chats_list.count() - 1).setData(Qt.UserRole, chat['chat_id'])

                key_data = self.db_manager.get_chat_key(chat['chat_id'])
                if key_data and key_data.get("shared_key"):
                    try:
                        self.chat_keys[chat['chat_id']] = base64.b64decode(key_data["shared_key"])
                        logger.debug(f"Loaded AES key for chat {chat['chat_id']} from DB.")
                    except (base64.binascii.Error, TypeError) as e:
                        logger.error(f"Failed to load/decode key for chat {chat['chat_id']} from DB: {e}")

        except Exception as e:
            logger.exception(f"Error loading chats from database: {e}")
            QMessageBox.critical(self, "Database Error", f"Could not load chats: {e}")

    def update_chat_list_item(self, chat_id: str, status: Optional[str] = None, new_text: Optional[str] = None):
        for i in range(self.chats_list.count()):
            item = self.chats_list.item(i)
            item_chat_id = item.data(Qt.UserRole)
            if item_chat_id == chat_id:
                if new_text:
                    item.setText(new_text)
                elif status:
                    current_text = item.text()
                    base_text = current_text.split(" [")[0]
                    item.setText(f"{base_text} [{status}]")
                logger.debug(f"Updated list item for chat {chat_id}")
                break

    def on_chat_selected(self, item):
        chat_id = item.data(Qt.UserRole)
        if chat_id:
            self.open_chat_tab(chat_id)
        else:
            logger.error(f"Could not get chat_id from selected list item: {item.text()}")

    def open_chat_by_id(self, chat_id: str):
        self.open_chat_tab(chat_id)

    def open_chat_tab(self, chat_id: str):
        try:
            data = self.api_client.get_encryption_status(chat_id, self.user_id)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                QMessageBox.warning(self, "Chat is closed", "This chat is no longer available for secure messaging.")
                return
            else:
                raise

        for i in range(self.chat_tabs.count()):
            widget = self.chat_tabs.widget(i)
            if isinstance(widget, ChatTab) and widget.chat_id == chat_id:
                self.chat_tabs.setCurrentIndex(i)
                logger.debug(f"Switched to existing tab for chat {chat_id}")
                return

        logger.info(f"Opening new tab for chat {chat_id}")

        chat_info = None
        for chat in self.db_manager.get_chats():
            if chat['chat_id'] == chat_id:
                chat_info = chat
                break

        if not chat_info:
            logger.error(f"Cannot open tab: Chat info not found in DB for {chat_id}")
            return

        chat_widget = ChatTab(chat_id, self.user_id, parent=self)

        chat_widget.send_message_requested.connect(self.send_chat_message)
        chat_widget.attach_file_requested.connect(self.attach_file_dialog)
        chat_widget.cancel_operation_requested.connect(self.cancel_current_operation)

        tab_title = f"{chat_id[:8]}... ({chat_info['algorithm'].name})"
        tab_index = self.chat_tabs.addTab(chat_widget, tab_title)
        self.chat_tabs.setCurrentIndex(tab_index)

        if not self.chat_tabs.tabBar().isVisible():
            self.chat_tabs.tabBar().setVisible(True)
            if isinstance(self.chat_tabs.widget(0), QLabel):
                logger.debug(f"closing 0 tab chat")
                self.chat_tabs.removeTab(0)

        self.load_chat_history(chat_id, chat_widget)

        if chat_id in self.chat_keys:
            chat_widget.set_send_button_state(True)
        else:
            chat_widget.set_send_button_state(False)

        if data.get("encryption_ready"):
            self.on_encryption_ready(chat_id)
        else:
            chat_widget.set_send_button_state(False)
            chat_widget.append_system_message("🔐 Establishing secure connection...")

    def load_chat_history(self, chat_id: str, chat_widget: ChatTab):
        logger.info(f"Loading message history for chat {chat_id}")
        messages = self.db_manager.get_messages(chat_id)
        if not messages:
            chat_widget.append_system_message("No messages yet.")
            return

        messages = sorted(messages, key=lambda msg: msg['timestamp'])

        for msg in messages:
            is_own = msg['sender'] == self.user_id
            chat_widget.append_message(
                sender=msg['sender'],
                text=msg['text'],
                timestamp=msg['timestamp'],
                is_own=is_own,
                is_file=msg['is_file'],
                file_name=msg['file_name'],
                file_path=None,
                file_bytes=msg['file_bytes']
            )
        logger.info(f"Loaded {len(messages)} messages for chat {chat_id}")

    def close_chat_tab(self, index: int):
        widget = self.chat_tabs.widget(index)
        if isinstance(widget, ChatTab):
            chat_id_to_close = widget.chat_id
            logger.info(f"Closing tab for chat {chat_id_to_close}")
            self.chat_tabs.removeTab(index)

            if self.current_chat_id == chat_id_to_close:
                logger.debug(f"Stopping WebSocket as active chat tab {chat_id_to_close} is closing.")
                self.current_chat_id = None
                self.statusBar().showMessage("No active chat.")

            if self.chat_tabs.count() == 1 and isinstance(self.chat_tabs.widget(0), QLabel):
                self.chat_tabs.tabBar().setVisible(False)
            elif self.chat_tabs.count() == 0:
                self.chat_tabs.addTab(self.no_chat_widget, "")
                self.chat_tabs.setTabEnabled(0, False)
                self.chat_tabs.tabBar().setVisible(False)

    def on_tab_changed(self, index: int):
        widget = self.chat_tabs.widget(index)
        new_chat_id = None
        if isinstance(widget, ChatTab):
            new_chat_id = widget.chat_id
            self.statusBar().showMessage(f"Active chat: {new_chat_id[:8]}...")

        if new_chat_id != self.current_chat_id:
            logger.debug(f"Tab changed. Old: {self.current_chat_id}, New: {new_chat_id}")

            if new_chat_id:
                i = 0
            else:
                self.current_chat_id = None
                self.statusBar().showMessage("No active chat selected.")

    def create_chat_dialog(self):
        dialog = CreateChatDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            algorithm = dialog.get_algorithm()
            mode = dialog.get_mode()
            padding = dialog.get_padding()

            self.statusBar().showMessage("Creating new chat...")
            try:
                response = self.api_client.create_chat(self.user_id, algorithm.name,
                                                       mode.name if hasattr(mode, 'name') else str(mode),
                                                       padding.name if hasattr(padding, 'name') else str(padding))
                chat_id = response.get("chat_id")

                if not chat_id:
                    raise ValueError("Invalid response from server during chat creation.")

                dh_params = self.api_client.get_dh_params(chat_id)
                p = int(dh_params.get('p'))
                g = int(dh_params.get('g'))
                logger.info(f"Chat {chat_id} created. DH params received: p={p}, g={g}")

                created_at = datetime.now().isoformat()
                self.db_manager.save_chat(
                    chat_id, algorithm, mode, padding, created_at,
                    "waiting_dh", is_creator=True
                )

                status_indicator = " [waiting]"
                list_item_text = f"{chat_id[:8]}... ({algorithm.name}/{mode.name}){status_indicator}"
                self.chats_list.addItem(list_item_text)
                item = self.chats_list.item(self.chats_list.count() - 1)
                item.setData(Qt.UserRole, chat_id)

                self.statusBar().showMessage(f"Chat {chat_id[:8]} created. Waiting for participant...")

                self.initiate_diffie_hellman(chat_id, p, g)

                self.open_chat_tab(chat_id)

            except Exception as e:
                logger.exception("Failed to create chat:")
                QMessageBox.critical(self, "Chat Creation Failed",
                                     f"Error creating chat: {str(e)}\n\n")
                self.statusBar().showMessage("Chat creation failed.")

    def join_chat_dialog(self):
        dialog = JoinChatDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            chat_id = dialog.get_chat_id()
            if not chat_id:
                QMessageBox.warning(self, "Input Error", "Please enter a valid Chat ID.")
                return

            self.statusBar().showMessage(f"Joining chat {chat_id[:8]}...")
            try:
                existing_chat = next((c for c in self.db_manager.get_chats() if c['chat_id'] == chat_id), None)
                if existing_chat:
                    logger.info(f"Chat {chat_id} already exists locally. Opening tab.")
                    self.open_chat_tab(chat_id)
                    self.statusBar().showMessage(f"Opened existing chat {chat_id[:8]}.")
                    return

                response = self.api_client.join_chat(chat_id, self.user_id)
                dh_params = response.get("dh_params")
                algorithm = EncryptionAlgorithm[response.get("algorithm")]

                if not dh_params:
                    dh_params = self.api_client.get_dh_params(chat_id)

                p = int(dh_params.get('p'))
                g = int(dh_params.get('g'))
                logger.info(f"Successfully joined chat {chat_id}. DH params: p={p}, g={g}")

                created_at = datetime.now().isoformat()
                self.db_manager.save_chat(
                    chat_id=chat_id,
                    algorithm=algorithm,
                    mode=response.get("encryption_mode"),
                    padding=response.get("padding_mode"),
                    created_at=created_at,
                    status="waiting_dh",
                    is_creator=False
                )

                self.add_chat_to_list(chat_id, algorithm.name, "waiting_dh")
                self.statusBar().showMessage(f"Joined chat {chat_id[:8]}. Performing key exchange...")

                self.initiate_diffie_hellman(chat_id, p, g)

                self.open_chat_tab(chat_id)

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    QMessageBox.critical(self, "Join Failed", f"Chat with ID '{chat_id}' not found or already closed.")
                elif e.response.status_code == 403:
                    QMessageBox.critical(self, "Join Failed",
                                         f"Cannot join chat '{chat_id}'. It might be full or you don't have permission.")
                else:
                    QMessageBox.critical(self, "Join Failed", f"Server error joining chat: {e}")
                self.statusBar().showMessage("Failed to join chat.")
            except Exception as e:
                logger.exception(f"An unexpected error occurred during joining chat {chat_id}:")
                QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
                self.statusBar().showMessage("Failed to join chat.")

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    QMessageBox.critical(self, "Join Failed", f"Chat with ID '{chat_id}' not found or already closed.")
                elif e.response.status_code == 403:
                    QMessageBox.critical(self, "Join Failed",
                                         f"Cannot join chat '{chat_id}'. It might be full or you don't have permission.")
                else:
                    QMessageBox.critical(self, "Join Failed", f"Server error joining chat: {e}")
                self.statusBar().showMessage("Failed to join chat.")
            except (requests.exceptions.RequestException, ConnectionError, TimeoutError, ValueError) as e:
                logger.exception(f"Failed to join chat {chat_id}:")
                QMessageBox.critical(self, "Join Failed", f"Error joining chat: {e}")
                self.statusBar().showMessage("Failed to join chat.")
            except Exception as e:
                logger.exception(f"An unexpected error occurred during joining chat {chat_id}:")
                QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
                self.statusBar().showMessage("Failed to join chat.")

    def add_chat_to_list(self, chat_id, algorithm, status):
        list_item_text = f"{chat_id[:8]}... ({algorithm}) [{status}]"
        self.chats_list.addItem(list_item_text)
        item = self.chats_list.item(self.chats_list.count() - 1)
        item.setData(Qt.UserRole, chat_id)
        logger.info(f"Added chat {chat_id} to list widget.")

    def initiate_diffie_hellman(self, chat_id: str, p: int, g: int):
        logger.info(f"Initiating Diffie-Hellman key exchange for chat {chat_id}...")
        try:
            private_key = DiffieHellman.generate_private_key(p)
            public_key = DiffieHellman.generate_public_key(p, g, private_key)
            logger.debug(f"DH: Generated local keys for {chat_id}. Public key: {public_key}")

            self.db_manager.save_keys(chat_id, None, p, g, private_key, public_key, None)

            self.api_client.store_public_key(chat_id, self.user_id, public_key)
            logger.info(f"DH: Sent public key for {chat_id} to server.")

            self.request_participant_key(chat_id, private_key, p)

        except (requests.exceptions.RequestException, ConnectionError, TimeoutError, ValueError) as e:
            logger.exception(f"Diffie-Hellman initiation error for {chat_id}:")
            QMessageBox.critical(self, "Key Exchange Failed", f"Error during key exchange setup: {e}")
            self.db_manager.update_chat_status(chat_id, "dh_failed")
            self.update_chat_list_item(chat_id, status="dh_failed")
        except Exception as e:
            logger.exception(f"Unexpected DH initiation error for {chat_id}:")
            QMessageBox.critical(self, "Key Exchange Error", f"An unexpected error occurred: {e}")
            self.db_manager.update_chat_status(chat_id, "dh_failed")
            self.update_chat_list_item(chat_id, status="dh_failed")

    def request_participant_key(self, chat_id: str, local_private_key: int, p: int):
        logger.info(f"Requesting participant's public key for chat {chat_id}...")
        try:
            response = self.api_client.get_participant_key(chat_id, self.user_id)
            other_public_key = response.get("public_key")

            if other_public_key:
                other_public_key = int(other_public_key)
                logger.info(f"DH: Received participant's public key for {chat_id}: {other_public_key}")
                self.compute_shared_secret(chat_id, local_private_key, other_public_key, p)
            else:
                logger.info(f"DH: Participant's key for {chat_id} not yet available. Waiting for WebSocket signal.")

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"DH: Participant's key for {chat_id} not found via API (expected, waiting for WS).")
            else:
                logger.error(f"DH: HTTP error getting participant key for {chat_id}: {e}")
                QMessageBox.warning(self, "Key Exchange", f"Could not get participant key: {e}")
                self.db_manager.update_chat_status(chat_id, "dh_failed")
                self.update_chat_list_item(chat_id, status="dh_failed")
        except (requests.exceptions.RequestException, ConnectionError, TimeoutError, ValueError) as e:
            logger.error(f"DH: Error requesting participant key for {chat_id}: {e}")
            QMessageBox.warning(self, "Key Exchange Error", f"Error getting participant key: {e}")
            self.db_manager.update_chat_status(chat_id, "dh_failed")
            self.update_chat_list_item(chat_id, status="dh_failed")

    def compute_shared_secret(self, chat_id: str, local_private_key: int, other_public_key: int, p: int):
        try:
            shared_secret_int = DiffieHellman.generate_shared_secret(p, other_public_key, local_private_key)
            logger.debug(f"DH: Calculated shared secret (int) for {chat_id}: {shared_secret_int}")

            aes_key = derive_cipher_key_16(shared_secret_int)
            logger.info(f"DH: Derived AES key for chat {chat_id}.")

            self.chat_keys[chat_id] = aes_key
            aes_key_b64 = base64.b64encode(aes_key).decode('utf-8')
            key_data = self.db_manager.get_chat_key(chat_id)
            if key_data:
                self.db_manager.save_keys(
                    chat_id, aes_key_b64,
                    key_data.get('p'), key_data.get('g'),
                    key_data.get('private_key'), key_data.get('public_key'),
                    other_public_key
                )
            else:
                logger.error(f"Cannot save final keys for {chat_id}, initial key data missing from DB.")
                raise ValueError("Initial key data missing, cannot save shared key.")

            self.db_manager.update_chat_status(chat_id, "active")
            self.update_chat_list_item(chat_id, status="active")
            self.on_encryption_ready(chat_id)

        except Exception as e:
            logger.exception(f"Error computing/saving shared secret for {chat_id}: {e}")
            QMessageBox.critical(self, "Key Exchange Error", f"Failed to finalize secure connection: {e}")
            self.db_manager.update_chat_status(chat_id, "dh_failed")
            self.update_chat_list_item(chat_id, status="dh_failed")

    @pyqtSlot(str)
    def on_encryption_ready(self, chat_id: str):
        logger.info(f"Received encryption_ready signal via WebSocket for chat {chat_id}.")

        if chat_id in self.chat_keys:
            logger.debug(f"AES key already exists for {chat_id}. Ensuring UI is enabled.")
        else:
            logger.info(f"AES key not found for {chat_id}. Attempting to fetch participant key and compute secret.")
            key_data = self.db_manager.get_chat_key(chat_id)
            if not key_data or not key_data.get('private_key') or not key_data.get('p'):
                logger.error(f"Cannot complete DH for {chat_id}: Missing local private key or parameters in DB.")
                QMessageBox.warning(self, "Key Exchange Error",
                                    "Missing local key information. Cannot complete key exchange.")
                self.db_manager.update_chat_status(chat_id, "dh_failed")
                self.update_chat_list_item(chat_id, status="dh_failed")
                return

            local_private_key = key_data['private_key']
            p = key_data['p']

            self.request_participant_key(chat_id, local_private_key, p)

        for i in range(self.chat_tabs.count()):
            widget = self.chat_tabs.widget(i)
            if isinstance(widget, ChatTab) and widget.chat_id == chat_id:
                if chat_id in self.chat_keys:
                    widget.set_send_button_state(True)
                    widget.append_system_message("Secure connection established. You can now send messages.")
                    self.statusBar().showMessage(f"Chat {chat_id[:8]} is active and secure.")
                    self.db_manager.update_chat_status(chat_id, "active")
                    self.update_chat_list_item(chat_id, status="active")
                else:
                    logger.warning(f"Encryption ready signal received for {chat_id}, but AES key still not available.")
                    widget.set_send_button_state(False)
                    widget.append_system_message("Error establishing full secure connection.")
                    self.statusBar().showMessage(f"Error securing chat {chat_id[:8]}.")
                break

    def send_chat_message(self, message_text: str):
        current_tab = self.get_current_chat_tab()
        if not current_tab:
            logger.error("Cannot send message: No active chat tab.")
            return

        chat_id = current_tab.chat_id
        aes_key = self.chat_keys.get(chat_id)

        if not aes_key:
            QMessageBox.warning(self, "Error", "Cannot send message: Encryption key not available for this chat.")
            return

        chat_info = next((c for c in self.db_manager.get_chats() if c['chat_id'] == chat_id), None)
        if not chat_info:
            logger.error(f"Cannot send message: Chat info not found for {chat_id}")
            return

        algorithm = chat_info['algorithm']
        mode = chat_info['mode']
        padding_mode = chat_info['padding']

        logger.debug(f"Preparing to send message to chat {chat_id} using {algorithm.name}")
        current_tab.show_progress("Encrypting...")

        self.encryption_worker = EncryptionWorker(
            crypto_manager=self.crypto_manager,
            algorithm=algorithm,
            key=aes_key,
            data=message_text.encode('utf-8'),
            mode=mode,
            padding_mode=padding_mode
        )

        self.encryption_worker.progress.connect(current_tab.update_progress)
        self.encryption_worker.result.connect(
            lambda result: self.on_encryption_complete(chat_id, result, is_file=False)
        )
        self.encryption_worker.error.connect(
            lambda error: QMessageBox.critical(self, "Encryption Error", error)
        )
        self.encryption_worker.finished.connect(
            lambda: current_tab.hide_progress() if current_tab else None
        )

        self.encryption_worker.start()

    def attach_file_dialog(self):
        current_tab = self.get_current_chat_tab()
        if not current_tab:
            logger.error("Cannot attach file: No active chat tab.")
            return

        chat_id = current_tab.chat_id
        if chat_id not in self.chat_keys:
            QMessageBox.warning(self, "Error", "Cannot send file: Encryption key not available for this chat.")
            return

        options = QFileDialog.Options()
        file_path_str, _ = QFileDialog.getOpenFileName(
            self, "Select File to Send", "",
            "All Files (*);;Text Files (*.txt);;Images (*.png *.jpg *.jpeg *.gif)",
            options=options
        )

        if file_path_str:
            file_path = Path(file_path_str)
            if file_path.exists() and file_path.is_file():
                file_size = file_path.stat().st_size
                max_size = 10 * 1024 * 1024  # 10 MB

                if file_size == 0:
                    QMessageBox.warning(self, "File Empty", "Cannot send an empty file.")
                    return

                if file_size > max_size:
                    QMessageBox.warning(
                        self, "File Too Large",
                        f"File size ({file_size / 1024 / 1024:.1f} MB) exceeds the limit of {max_size / 1024 / 1024:.0f} MB."
                    )
                    return

                self.send_file(file_path)
            else:
                QMessageBox.warning(self, "File Error", "Selected path is not a valid file.")

    def send_file(self, file_path: Path):
        current_tab = self.get_current_chat_tab()
        if not current_tab: return

        chat_id = current_tab.chat_id
        aes_key = self.chat_keys.get(chat_id)
        if not aes_key: return

        logger.info(f"Preparing to send file: {file_path.name} to chat {chat_id}")
        current_tab.show_progress(f"Encrypting {file_path.name}...")

        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
        except IOError as e:
            logger.exception(f"Error reading file {file_path}: {e}")
            QMessageBox.critical(self, "File Error", f"Could not read file: {e}")
            current_tab.hide_progress()
            return

        chat_info = next((c for c in self.db_manager.get_chats() if c['chat_id'] == chat_id), None)
        if not chat_info:
            logger.error(f"Cannot send message: Chat info not found for {chat_id}")
            return

        algorithm = chat_info['algorithm']
        mode = chat_info['mode']
        padding_mode = chat_info['padding']

        self.encryption_worker = EncryptionWorker(
            crypto_manager=self.crypto_manager,
            algorithm=algorithm,
            key=aes_key,
            data=file_data,
            mode=mode,
            padding_mode=padding_mode
        )
        self.encryption_worker.progress.connect(current_tab.update_progress)
        self.encryption_worker.error.connect(self.on_encryption_error)
        self.encryption_worker.result.connect(
            lambda result_tuple: self.on_encryption_complete(chat_id, result_tuple, is_file=True,
                                                             file_name=file_path.name)
        )

        try:
            self.encryption_worker.finished.disconnect()
        except TypeError:
            pass
        self.encryption_worker.finished.connect(self.on_worker_finished)

        self.encryption_worker.start()

    @pyqtSlot(str)
    def on_encryption_error(self, error_message: str):
        logger.error(f"Encryption Worker Error: {error_message}")
        QMessageBox.critical(self, "Encryption Error", f"Failed to encrypt data: {error_message}")
        current_tab = self.get_current_chat_tab()
        if current_tab:
            current_tab.hide_progress()
        self.encryption_worker = None

    @pyqtSlot(tuple)
    def on_encryption_complete(self, chat_id: str, result_tuple: tuple, is_file: bool, file_name: Optional[str] = None):
        encrypted_base64, iv_base64 = result_tuple
        logger.info(f"Encryption complete for chat {chat_id}. Sending {'file' if is_file else 'message'}...")

        current_tab = self.get_current_chat_tab()
        if not current_tab or current_tab.chat_id != chat_id:
            logger.warning(f"Encryption completed for chat {chat_id}, but the tab is not active or found.")
            return

        current_tab.update_progress(100)
        current_tab.show_progress("Sending...")

        try:
            timestamp = datetime.now().isoformat()
            response = self.api_client.send_message(
                chat_id=chat_id,
                user_id=self.user_id,
                encrypted_message=encrypted_base64,
                iv_nonce=iv_base64,
                encryption_mode="CBC",
                padding_mode="PKCS7",
                timestamp=timestamp,
                is_file=is_file,
                file_name=file_name
            )
            message_id = response.get("message_id")

            logger.info(f"Message/File sent successfully to {chat_id}. Message ID: {message_id}")

            if is_file:
                current_tab.append_message(
                    self.user_id, '', timestamp, is_own=True,
                    is_file=True, file_name=file_name, file_path=None,
                    file_bytes=self.encryption_worker.data
                )
                self.db_manager.save_message(
                    message_id, chat_id, self.user_id, timestamp,
                    encrypted_base64, f"File: {file_name}",
                    iv_base64, "CBC", "PKCS7",
                    is_file=True, file_name=file_name, file_path=None,
                    file_bytes=self.encryption_worker.data
                )
            else:
                original_text = self.encryption_worker.data.decode(
                    'utf-8') if self.encryption_worker else "[Original text not available]"
                current_tab.append_message(self.user_id, original_text, timestamp, is_own=True)
                self.db_manager.save_message(
                    message_id, chat_id, self.user_id, timestamp,
                    encrypted_base64, original_text,
                    iv_base64, "CBC", "PKCS7",
                    is_file=False
                )

            current_tab.hide_progress()

        except (requests.exceptions.RequestException, ConnectionError, TimeoutError, ValueError) as e:
            logger.exception(f"Failed to send message/file to chat {chat_id}:")
            QMessageBox.critical(self, "Send Error", f"Failed to send: {e}")
            current_tab.hide_progress()
        except Exception as e:
            logger.exception(f"Unexpected error sending message/file to {chat_id}:")
            QMessageBox.critical(self, "Send Error", f"An unexpected error occurred: {e}")
            current_tab.hide_progress()
        finally:
            self.encryption_worker = None

    @pyqtSlot(dict)
    def handle_incoming_message(self, msg_data: dict):
        chat_id = msg_data.get("chat_id")
        chat_data = self.db_manager.get_chat_encryption_params(chat_id)
        sender = msg_data.get("sender")
        encrypted_message_b64 = msg_data.get("encrypted_message")
        iv_b64 = msg_data.get("iv_nonce")
        timestamp = msg_data.get("timestamp", datetime.now().isoformat())
        message_id = msg_data.get("message_id", str(uuid.uuid4()))
        encryption_mode = chat_data['mode']
        padding_mode = chat_data['padding']

        logger.info(f"Received encrypted message {message_id} from {sender} in chat {chat_id}")

        target_tab: Optional[ChatTab] = None
        for i in range(self.chat_tabs.count()):
            widget = self.chat_tabs.widget(i)
            if isinstance(widget, ChatTab) and widget.chat_id == chat_id:
                target_tab = widget
                break

        if not target_tab:
            logger.warning(f"Received message for chat {chat_id}, but no corresponding tab is open. Storing message.")

        aes_key = self.chat_keys.get(chat_id)
        if not aes_key:
            logger.error(f"Cannot decrypt message {message_id} for chat {chat_id}: AES key not found.")
            self.db_manager.save_message(
                message_id, chat_id, 'system', timestamp,
                encrypted_message_b64, "[Decryption key missing]", iv_b64,
                encryption_mode.name, padding_mode.name, is_file=False
            )
            if target_tab:
                target_tab.append_system_message(
                    "🔒 You were not online during the key exchange for this message, so decryption is not possible.")
            return

        if target_tab:
            target_tab.show_progress("Decrypting message...")

        decryption_context = {
            "message_id": message_id,
            "chat_id": chat_id,
            "sender": sender,
            "timestamp": timestamp,
            "encrypted_message_b64": encrypted_message_b64,
            "iv_b64": iv_b64,
            "encryption_mode": encryption_mode.name,
            "padding_mode": padding_mode.name,
            "is_file": False
        }

        self.decryption_worker = DecryptionWorker(
            self.crypto_manager,
            algorithm=chat_data['algorithm'],
            key=aes_key,
            encrypted_data_b64=encrypted_message_b64,
            iv_b64=iv_b64,
            mode=encryption_mode,
            padding_mode=padding_mode
        )

        self.decryption_worker.result.connect(
            lambda decrypted_bytes: self.on_decryption_complete(decrypted_bytes, decryption_context)
        )
        self.decryption_worker.error.connect(
            lambda error_msg: self.on_decryption_error(error_msg, decryption_context)
        )
        if target_tab:
            self.decryption_worker.progress.connect(target_tab.update_progress)
        try:
            self.decryption_worker.finished.disconnect()
        except TypeError:
            pass
        self.decryption_worker.finished.connect(self.on_worker_finished)

        self.decryption_worker.start()

    def ask_user_save_path(self, suggested_path: Path, file_name: str) -> Optional[Path]:
        options = QFileDialog.Options()
        save_path_str, _ = QFileDialog.getSaveFileName(
            self,
            f"Save Received File '{file_name}'?",
            str(suggested_path),
            f"Files (*{suggested_path.suffix});;All Files (*)",
            options=options
        )
        return Path(save_path_str) if save_path_str else None

    @pyqtSlot(dict)
    def handle_incoming_file(self, msg_data: dict):
        chat_id = msg_data.get("chat_id")
        chat_data = self.db_manager.get_chat_encryption_params(chat_id)
        sender = msg_data.get("sender")
        file_name = msg_data.get("file_name", "unknown_file")
        encrypted_file_b64 = msg_data.get("encrypted_message")
        iv_b64 = msg_data.get("iv_nonce")
        timestamp = msg_data.get("timestamp", datetime.now().isoformat())
        message_id = msg_data.get("message_id", str(uuid.uuid4()))
        encryption_mode = chat_data['mode']
        padding_mode = chat_data['padding']

        logger.info(f"Received encrypted file '{file_name}' ({message_id}) from {sender} in chat {chat_id}")

        target_tab: Optional[ChatTab] = None
        for i in range(self.chat_tabs.count()):
            widget = self.chat_tabs.widget(i)
            if isinstance(widget, ChatTab) and widget.chat_id == chat_id:
                target_tab = widget
                break

        aes_key = self.chat_keys.get(chat_id)
        if not aes_key:
            logger.error(f"Cannot decrypt file {message_id} for chat {chat_id}: AES key not found.")
            self.db_manager.save_message(
                message_id, chat_id, sender, timestamp,
                encrypted_file_b64, f"[File: {file_name} - Key missing]", iv_b64,
                encryption_mode, padding_mode, is_file=True, file_name=file_name
            )
            if target_tab:
                target_tab.append_system_message(
                    f"Error: Received file '{file_name}' but couldn't decrypt (key missing).")
            return

        download_dir = Path.home() / "Downloads" / "SecureChat"
        download_dir.mkdir(parents=True, exist_ok=True)

        if target_tab:
            target_tab.show_progress(f"Decrypting {file_name}...")

        decryption_context = {
            "message_id": message_id,
            "chat_id": chat_id,
            "sender": sender,
            "timestamp": timestamp,
            "encrypted_message_b64": encrypted_file_b64,
            "iv_b64": iv_b64,
            "encryption_mode": encryption_mode.name,
            "padding_mode": padding_mode.name,
            "is_file": True,
            "file_name": file_name,
            "save_path": None
        }

        chat_data = self.db_manager.get_chat_encryption_params(chat_id)

        self.decryption_worker = DecryptionWorker(
            self.crypto_manager,
            algorithm=chat_data['algorithm'],
            key=aes_key,
            encrypted_data_b64=encrypted_file_b64,
            iv_b64=iv_b64,
            mode=encryption_mode,
            padding_mode=padding_mode
        )

        self.decryption_worker.result.connect(
            lambda decrypted_bytes: self.on_decryption_complete(decrypted_bytes, decryption_context)
        )
        self.decryption_worker.error.connect(
            lambda error_msg: self.on_decryption_error(error_msg, decryption_context)
        )
        if target_tab:
            self.decryption_worker.progress.connect(target_tab.update_progress)
        try:
            self.decryption_worker.finished.disconnect()
        except TypeError:
            pass
        self.decryption_worker.finished.connect(self.on_worker_finished)

        self.decryption_worker.start()

    @pyqtSlot(str, dict)
    def on_decryption_error(self, error_message: str, context: dict):
        message_id = context["message_id"]
        chat_id = context["chat_id"]
        logger.error(f"Decryption Worker Error for message/file {message_id} in chat {chat_id}: {error_message}")
        QMessageBox.critical(self, "Decryption Error", f"Failed to decrypt data: {error_message}")

        target_tab = self.find_chat_tab(chat_id)
        if target_tab:
            target_tab.hide_progress()
            if context["is_file"]:
                target_tab.append_system_message(f"Error decrypting file '{context['file_name']}'.")
            else:
                target_tab.append_system_message("Error decrypting message.")

        decrypted_placeholder = f"[Decryption Error: {error_message[:50]}]"
        if context["is_file"]:
            decrypted_placeholder = f"[File: {context['file_name']} - Decryption Error]"

        self.db_manager.save_message(
            message_id, chat_id, context["sender"], context["timestamp"],
            context["encrypted_message_b64"], decrypted_placeholder, context["iv_b64"],
            context["encryption_mode"], context["padding_mode"],
            is_file=context["is_file"], file_name=context.get("file_name")
        )
        self.decryption_worker = None

    @pyqtSlot(bytes, dict)
    def on_decryption_complete(self, decrypted_bytes: bytes, context: dict):
        message_id = context["message_id"]
        chat_id = context["chat_id"]
        logger.info(f"Decryption complete for message/file {message_id} in chat {chat_id}.")

        target_tab = self.find_chat_tab(chat_id)
        if target_tab:
            target_tab.update_progress(100)

        decrypted_text = None
        file_save_path = None

        if not context.get("is_file", False):
            decrypted_text = decrypted_bytes.decode('utf-8')
            is_binary = False
        else:
            is_binary = True
            decrypted_text = f"[Binary data, size: {len(decrypted_bytes)} bytes]"

            if context.get("is_file", False):
                save_path = context.get("save_path")
                if save_path:
                    try:
                        with open(save_path, "wb") as f:
                            f.write(decrypted_bytes)
                        file_save_path = str(save_path)
                        decrypted_text = f"[File saved to: {file_save_path}]"
                    except IOError as e:
                        logger.error(f"Error saving file: {e}")
                        decrypted_text = f"[File save error: {str(e)}]"

        if target_tab:
            target_tab.hide_progress()
            is_own = context["sender"] == self.user_id
            if context.get("is_file", False):
                decrypted_text = f"[Binary data, size: {len(decrypted_bytes)} bytes]"
                file_save_path = None  # Не сохраняем сразу

                if target_tab:
                    is_own = context["sender"] == self.user_id
                    target_tab.append_message(
                        context["sender"], decrypted_text, context["timestamp"], is_own=is_own,
                        is_file=True, file_name=context.get("file_name"), file_path=None,
                        file_bytes=decrypted_bytes  # передаём байты
                    )
            else:
                target_tab.append_message(
                    context["sender"], decrypted_text, context["timestamp"], is_own=is_own
                )

        self.db_manager.save_message(
            message_id, chat_id, context["sender"], context["timestamp"],
            context["encrypted_message_b64"],
            decrypted_text,
            context["iv_b64"],
            context["encryption_mode"], context["padding_mode"],
            is_file=context.get("is_file", False),
            file_name=context.get("file_name"),
            file_path=file_save_path,
            file_bytes=decrypted_bytes
        )

    def find_chat_tab(self, chat_id: str) -> Optional[ChatTab]:
        for i in range(self.chat_tabs.count()):
            widget = self.chat_tabs.widget(i)
            if isinstance(widget, ChatTab) and widget.chat_id == chat_id:
                return widget
        return None

    @pyqtSlot()
    def on_worker_finished(self):
        current_tab = self.get_current_chat_tab()
        if current_tab and (self.encryption_worker or self.decryption_worker):
            if current_tab.progress_bar.isVisible():
                logger.warning("Worker finished, hiding progress bar.")
                current_tab.hide_progress()
        sender = self.sender()
        if sender == self.encryption_worker:
            self.encryption_worker = None
        elif sender == self.decryption_worker:
            self.decryption_worker = None

    def cancel_current_operation(self):
        if self.encryption_worker and self.encryption_worker.isRunning():
            logger.info("Requesting cancellation of encryption worker.")
            self.encryption_worker.cancel()
        elif self.decryption_worker and self.decryption_worker.isRunning():
            logger.info("Requesting cancellation of decryption worker.")
            self.decryption_worker.cancel()
        else:
            logger.debug("No active encryption/decryption operation to cancel.")

    def show_chat_context_menu(self, position):
        item = self.chats_list.itemAt(position)
        if not item:
            return

        chat_id = item.data(Qt.UserRole)
        if not chat_id:
            logger.error("Context menu: Could not get chat_id from list item.")
            return

        chat_info = next((c for c in self.db_manager.get_chats() if c['chat_id'] == chat_id), None)
        if not chat_info:
            logger.error(f"Context menu: Chat info not found in DB for {chat_id}")
            return

        menu = QMenu()

        open_action = menu.addAction(f"Open Chat ({chat_id[:8]}...)")
        open_action.triggered.connect(lambda: self.open_chat_by_id(chat_id))

        menu.addSeparator()

        copy_id_action = menu.addAction("Copy Chat ID")
        copy_id_action.triggered.connect(lambda: QApplication.clipboard().setText(chat_id))

        menu.addSeparator()

        leave_action = menu.addAction("Leave Chat")
        leave_action.triggered.connect(lambda: self.leave_chat(chat_id))

        if chat_info.get('is_creator', False):
            close_action = menu.addAction("Close Chat (for All)")
            close_action.triggered.connect(lambda: self.close_chat(chat_id))

        menu.exec_(self.chats_list.viewport().mapToGlobal(position))

    def leave_chat(self, chat_id):
        reply = QMessageBox.question(self, 'Leave Chat',
                                     f"Are you sure you want to leave chat {chat_id[:8]}...?\n"
                                     "You will lose access and local history will be deleted.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            logger.info(f"Attempting to leave chat {chat_id}...")
            self.statusBar().showMessage(f"Leaving chat {chat_id[:8]}...")
            try:
                response = self.api_client.leave_chat(chat_id, self.user_id)

                if response.get("status") == "leaved" or response.get("message", "").startswith("Successfully left"):
                    logger.info(f"Successfully left chat {chat_id} via API.")
                    self.cleanup_after_leave_or_close(chat_id)
                    QMessageBox.information(self, "Chat Left", f"You have left chat {chat_id[:8]}...")
                    self.statusBar().showMessage(f"Left chat {chat_id[:8]}.")

                else:
                    error_msg = response.get("message", "Unknown reason")
                    logger.error(f"API indicated failure to leave chat {chat_id}: {error_msg}")
                    QMessageBox.warning(self, "Leave Failed", f"Could not leave chat: {error_msg}")
                    self.statusBar().showMessage(f"Failed to leave chat {chat_id[:8]}.")

            except requests.exceptions.HTTPError as e:
                logger.exception(f"HTTP error leaving chat {chat_id}:")
                QMessageBox.critical(self, "Leave Failed",
                                     f"Server error leaving chat: {e.response.status_code} - {e.response.text}")
                self.statusBar().showMessage(f"Failed to leave chat {chat_id[:8]}.")
            except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
                logger.exception(f"Network error leaving chat {chat_id}:")
                QMessageBox.critical(self, "Leave Failed", f"Network error: {e}")
                self.statusBar().showMessage(f"Failed to leave chat {chat_id[:8]}.")
            except Exception as e:
                logger.exception(f"Unexpected error leaving chat {chat_id}:")
                QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
                self.statusBar().showMessage(f"Failed to leave chat {chat_id[:8]}.")

    def close_chat(self, chat_id):
        reply = QMessageBox.question(self, 'Close Chat',
                                     f"Are you sure you want to permanently close chat {chat_id[:8]}... for ALL participants?\n"
                                     "This action cannot be undone and local history will be deleted.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            logger.info(f"Attempting to close chat {chat_id} as creator...")
            self.statusBar().showMessage(f"Closing chat {chat_id[:8]}...")
            try:
                response = self.api_client.close_chat(chat_id, self.user_id)

                if response.get("status") == "closed" or response.get("message", "").startswith("Chat closed"):
                    logger.info(f"Successfully closed chat {chat_id} via API.")
                    self.cleanup_after_leave_or_close(chat_id)
                    QMessageBox.information(self, "Chat Closed", f"Chat {chat_id[:8]}... has been closed.")
                    self.statusBar().showMessage(f"Closed chat {chat_id[:8]}.")
                else:
                    error_msg = response.get("message", "Unknown reason")
                    logger.error(f"API indicated failure to close chat {chat_id}: {error_msg}")
                    if "not the creator" in error_msg.lower():
                        QMessageBox.warning(self, "Close Failed",
                                            "You are not the creator of this chat and cannot close it.")
                    else:
                        QMessageBox.warning(self, "Close Failed", f"Could not close chat: {error_msg}")
                    self.statusBar().showMessage(f"Failed to close chat {chat_id[:8]}.")

            except requests.exceptions.HTTPError as e:
                logger.exception(f"HTTP error closing chat {chat_id}:")
                if e.response.status_code == 403:
                    QMessageBox.critical(self, "Close Failed",
                                         "You do not have permission to close this chat (only the creator can).")
                elif e.response.status_code == 404:
                    QMessageBox.critical(self, "Close Failed",
                                         "Chat not found. It might have already been closed or deleted.")
                else:
                    QMessageBox.critical(self, "Close Failed",
                                         f"Server error closing chat: {e.response.status_code} - {e.response.text}")
                self.statusBar().showMessage(f"Failed to close chat {chat_id[:8]}.")
            except (requests.exceptions.RequestException, ConnectionError, TimeoutError) as e:
                logger.exception(f"Network error closing chat {chat_id}:")
                QMessageBox.critical(self, "Close Failed", f"Network error: {e}")
                self.statusBar().showMessage(f"Failed to close chat {chat_id[:8]}.")
            except Exception as e:
                logger.exception(f"Unexpected error closing chat {chat_id}:")
                QMessageBox.critical(self, "Error", f"An unexpected error occurred: {e}")
                self.statusBar().showMessage(f"Failed to close chat {chat_id[:8]}.")

    def cleanup_after_leave_or_close(self, chat_id):
        logger.debug(f"Performing cleanup for chat {chat_id} after leave/close.")
        self.close_tab_if_open(chat_id)

        if self.current_chat_id == chat_id:
            logger.info(f"Stopping WebSocket as chat {chat_id} is being left/closed.")
            self.current_chat_id = None
            self.statusBar().showMessage("No active chat.")

        self.remove_chat_from_list(chat_id)

        self.db_manager.delete_chat(chat_id)

        removed_key = self.chat_keys.pop(chat_id, None)
        if removed_key:
            logger.debug(f"Removed AES key for chat {chat_id} from memory cache.")

    def close_tab_if_open(self, chat_id):
        for i in range(self.chat_tabs.count()):
            widget = self.chat_tabs.widget(i)
            if isinstance(widget, ChatTab) and widget.chat_id == chat_id:
                logger.debug(f"Found open tab for chat {chat_id} at index {i}. Closing it.")
                is_current = (self.current_chat_id == chat_id)
                if is_current: self.current_chat_id = None

                self.chat_tabs.removeTab(i)

                if self.chat_tabs.count() == 1 and isinstance(self.chat_tabs.widget(0), QLabel):
                    self.chat_tabs.tabBar().setVisible(False)
                elif self.chat_tabs.count() == 0:
                    self.chat_tabs.addTab(self.no_chat_widget, "")
                    self.chat_tabs.setTabEnabled(0, False)
                    self.chat_tabs.tabBar().setVisible(False)
                break

    def remove_chat_from_list(self, chat_id):
        for i in range(self.chats_list.count()):
            item = self.chats_list.item(i)
            if item.data(Qt.UserRole) == chat_id:
                self.chats_list.takeItem(i)
                logger.debug(f"Removed chat {chat_id} from list widget.")
                break

    @pyqtSlot(str)
    def on_chat_closed_by_server(self, chat_id: str):
        logger.info(f"Received signal that chat {chat_id} was closed by the server/creator.")
        QMessageBox.information(self, "Chat Closed", f"Chat {chat_id[:8]}... has been closed by the creator.")
        self.cleanup_after_leave_or_close(chat_id)
        self.statusBar().showMessage(f"Chat {chat_id[:8]} closed by creator.")

    @pyqtSlot(dict)
    def on_user_left(self, data: dict):
        chat_id = data.get("chat_id")
        user_id = data.get("user_id")
        logger.info(f"User {user_id} left chat {chat_id}.")

        logger.info(f"Participant changed in chat {chat_id}. Resetting DH...")
        self.chat_keys.pop(chat_id, None)

        target_tab = self.find_chat_tab(chat_id)
        if target_tab:
            target_tab.append_system_message(f"User {user_id[:6]}... has left the chat.")
            target_tab.set_send_button_state(False)
            target_tab.append_system_message("You are now alone in this chat.")
            self.statusBar().showMessage(f"Participant left chat {chat_id[:8]}.")
            self.db_manager.update_chat_status(chat_id, "alone")
            self.update_chat_list_item(chat_id, status="alone")

    def closeEvent(self, event):
        logger.info("Close event triggered. Cleaning up...")

        if self.kafka_thread:
            self.kafka_worker.stop()
        if self.kafka_thread and self.kafka_thread.isRunning():
            self.kafka_thread.quit()
            self.kafka_thread.wait()

        if self.encryption_worker and self.encryption_worker.isRunning():
            logger.info("Stopping active encryption worker...")
            self.encryption_worker.cancel()
            self.encryption_worker.wait()

        if self.decryption_worker and self.decryption_worker.isRunning():
            logger.info("Stopping active decryption worker...")
            self.decryption_worker.cancel()
            self.decryption_worker.wait()

        self.db_manager.close_db()

        logger.info("Cleanup finished. Exiting application.")
        event.accept()