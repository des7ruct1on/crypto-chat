import logging
import mimetypes
import tempfile
import os
from typing import Optional
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton,
                             QTextEdit, QProgressBar,
                             QMessageBox, QLabel, QFileDialog, QStyle, QScrollArea,
                             QSlider, QToolButton, QSizePolicy,
                             QGraphicsView, QGraphicsScene)
from PyQt5.QtCore import Qt, pyqtSignal, QUrl, QSizeF
from PyQt5.QtGui import QPixmap, QImage, QFontMetrics, QTextOption
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem

from views.dialogs.image_preview import ImagePreviewDialog
from views.dialogs.gif_preview import GifPreviewDialog
from views.dialogs.text_preview import TextPreviewDialog
from views.dialogs.markdown_preview import MarkdownPreviewDialog
from views.labels.clickable_image import ClickableImage
from views.labels.clickable_label import ClickableLabel
from views.labels.clickable_gif import ClickableGifLabel

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ChatTab(QWidget):
    send_message_requested = pyqtSignal(str)
    attach_file_requested = pyqtSignal()
    cancel_operation_requested = pyqtSignal()
    invite_user_requested = pyqtSignal(str)

    def __init__(self, chat_id, user_id, parent=None):
        super().__init__(parent)
        self.chat_id = chat_id
        self.user_id = user_id
        self.is_encryption_ready = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # Messages area with modern styling
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: #1e1e1e;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QScrollBar:vertical {
                border: none;
                background: #2a2a2a;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.scroll_content = QWidget()
        self.messages_layout = QVBoxLayout(self.scroll_content)
        self.messages_layout.setContentsMargins(10, 10, 10, 10)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)

        # Input area with modern styling
        input_container = QWidget()
        input_container.setMaximumHeight(150)
        input_container.setStyleSheet("""
            background: #252525; 
            border-radius: 6px;
            border: 1px solid #333;
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)

        self.message_input = QTextEdit()
        self.message_input.setMaximumHeight(90)
        self.message_input.setPlaceholderText("Type your message here...")
        self.message_input.setStyleSheet("""
            QTextEdit {
                background: #2a2a2a;
                color: #e0e0e0;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                selection-background-color: #4a6fa5;
            }
            QTextEdit:focus {
                border: 1px solid #4a6fa5;
            }
        """)
        self.message_input.installEventFilter(self)

        self.attach_button = QPushButton()
        self.attach_button.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        self.attach_button.setToolTip("Attach File")
        self.attach_button.setFixedSize(36, 36)
        self.attach_button.setStyleSheet("""
            QPushButton {
                background: #3a3a3a;
                border: 1px solid #444;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: #444;
            }
            QPushButton:pressed {
                background: #333;
            }
        """)
        self.attach_button.clicked.connect(self.attach_file_requested.emit)

        self.send_button = QPushButton("Send")
        self.send_button.setFixedHeight(36)
        self.send_button.setStyleSheet("""
            QPushButton {
                background: #4a6fa5;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #5b7bb5;
            }
            QPushButton:pressed {
                background: #3a5a95;
            }
            QPushButton:disabled {
                background: #3a3a3a;
                color: #777;
                border: 1px solid #444;
            }
        """)
        self.send_button.clicked.connect(self.on_send_clicked)

        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.attach_button)
        input_layout.addWidget(self.send_button)

        # Progress bar with modern styling
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #333;
                border-radius: 6px;
                text-align: center;
                background: #2a2a2a;
                height: 22px;
                color: #ddd;
            }
            QProgressBar::chunk {
                background: #4a6fa5;
                border-radius: 5px;
            }
        """)

        # Cancel button with modern styling
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setVisible(False)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background: #5a5a5a;
                color: #e0e0e0;
                border: 1px solid #666;
                border-radius: 6px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #666;
            }
            QPushButton:pressed {
                background: #4a4a4a;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_operation_requested.emit)

        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(input_container)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.cancel_button)

        self.set_send_button_state(False)

    def eventFilter(self, source, event):
        if source is self.message_input and event.type() == event.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() == Qt.ShiftModifier:
                    return super().eventFilter(source, event)
                else:
                    self.on_send_clicked()
                    return True
        return super().eventFilter(source, event)

    def on_send_clicked(self):
        if not self.is_encryption_ready:
            QMessageBox.warning(self, "Cannot Send", "Encryption keys are not yet established for this chat.")
            return
        message_text = self.message_input.toPlainText().strip()
        if message_text:
            self.send_message_requested.emit(message_text)
            self.message_input.clear()
        else:
            logger.debug("Empty message ignored.")

    def set_send_button_state(self, enabled: bool):
        self.is_encryption_ready = enabled
        self.send_button.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)
        tooltip = "Attach File" if enabled else "Waiting for the other participant to join and establish encryption..."
        self.attach_button.setToolTip(tooltip)
        self.send_button.setToolTip("Press Enter to send, Shift+Enter for newline" if enabled else tooltip)
        self.message_input.setPlaceholderText("Enter message..." if enabled else tooltip)

    def append_message(self, sender: str, text: str, timestamp: str, is_own: bool, is_file: bool = False,
                       file_name: Optional[str] = None, file_path: Optional[str] = None,
                       file_bytes: Optional[bytes] = None):
        if sender == 'system' and text == '[Decryption key missing]':
            self.append_system_message(
                "🔒 You were not online during the key exchange for this message, so decryption is not possible.")
            return
        try:
            dt_obj = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt_obj.strftime('%H:%M:%S')
        except ValueError:
            formatted_time = timestamp

        sender_display = "You" if is_own else f"User_{sender[:6]}..."

        bubble = QWidget()
        bubble.setObjectName("messageBubble")

        # Modern message bubble styling
        if is_own:
            bubble.setStyleSheet("""
                QWidget#messageBubble {
                    background-color: #2a4a7a;
                    border-radius: 12px;
                    border: 1px solid #3a5a8a;
                    padding: 2px;
                }
            """)
        else:
            bubble.setStyleSheet("""
                QWidget#messageBubble {
                    background-color: #2a2a3a;
                    border-radius: 12px;
                    border: 1px solid #383848;
                    padding: 2px;
                }
            """)

        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header with modern styling
        header = QLabel(
            f"<span style='color: #aaaaaa; font-size: 10px; font-weight: 500;'>{sender_display}</span> <span style='color: #888888; font-size: 9px;'>{formatted_time}</span>")
        header.setStyleSheet("QLabel { background: transparent; }")
        layout.addWidget(header)

        def add_file_row(handle_file_row_click=None):
            file_icon = ClickableLabel()
            file_icon.setPixmap(self.style().standardIcon(QStyle.SP_FileIcon).pixmap(18, 18))
            file_icon.setStyleSheet("""
                QLabel { 
                    background: transparent; 
                    padding: 2px;
                }
            """)

            if handle_file_row_click is not None:
                file_icon.set_click_handler(lambda event: handle_file_row_click(event))

            file_label = QLabel(
                f"<span style='color: #dddddd; font-style: italic; font-size: 12px;'>{file_name}</span>")
            file_label.setStyleSheet("""
                QLabel { 
                    background: transparent; 
                    padding: 2px;
                }
            """)
            file_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            file_label.setMaximumWidth(200)
            file_label.setWordWrap(False)
            file_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

            metrics = QFontMetrics(file_label.font())
            elided_text = metrics.elidedText(file_name, Qt.ElideRight, 200)
            file_label.setText(
                f"<span style='color: #dddddd; font-style: italic; font-size: 12px;'>{elided_text}</span>")

            file_row = QHBoxLayout()
            file_row.setSpacing(6)
            file_row.addWidget(file_icon)
            file_row.addWidget(file_label)
            file_row.setAlignment(Qt.AlignLeft)

            file_row_container = QWidget()
            file_row_container.setStyleSheet("QWidget { background: transparent; }")
            file_row_container.setLayout(file_row)

            layout.addWidget(file_row_container)

        def handle_img_file_row_click(event, pixmap):
            if event.button() == Qt.LeftButton:
                dialog = ImagePreviewDialog(pixmap)
                dialog.exec_()

        def handle_gif_file_row_click(event, gif_bytes):
            if event.button() == Qt.LeftButton:
                dialog = GifPreviewDialog(gif_bytes)
                dialog.exec_()

        def handle_txt_file_row_click(event, text, title):
            if event.button() == Qt.LeftButton:
                dialog = TextPreviewDialog(text, title)
                dialog.exec_()

        def handle_md_file_row_click(event, text, title):
            if event.button() == Qt.LeftButton:
                dialog = MarkdownPreviewDialog(text, title)
                dialog.exec_()

        if is_file and file_bytes:
            mime_type, _ = mimetypes.guess_type(file_name or "")
            if mime_type is not None and mime_type.startswith("image") and not mime_type.endswith("gif"):
                image = QImage.fromData(file_bytes)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    add_file_row(lambda event: handle_img_file_row_click(event, pixmap))
                    img_label = ClickableImage(pixmap)
                    img_label.setStyleSheet("""
                        QLabel { 
                            background: transparent; 
                            border-radius: 6px;
                            border: 1px solid #444;
                        }
                    """)
                    layout.addWidget(img_label)
            elif mime_type is not None and mime_type.endswith("gif"):
                add_file_row(lambda event: handle_gif_file_row_click(event, file_bytes))
                gif_label = ClickableGifLabel(file_bytes)
                gif_label.setStyleSheet("""
                    QLabel { 
                        background: transparent; 
                        border-radius: 6px;
                        border: 1px solid #444;
                    }
                """)
                layout.addWidget(gif_label)
            elif mime_type == "text/plain":
                text = file_bytes.decode(errors="ignore")
                add_file_row(lambda event: handle_txt_file_row_click(event, text, file_name))
            elif mime_type in ("text/markdown", "text/x-markdown") or (file_name or "").lower().endswith(".md"):
                md_text = file_bytes.decode(errors="ignore")
                add_file_row(lambda event: handle_md_file_row_click(event, md_text, file_name))
            elif mime_type is not None and mime_type.startswith("video"):
                suffix = os.path.splitext(file_name or '')[-1]
                temp_video = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                temp_video.write(file_bytes)
                temp_video.close()

                add_file_row()

                scene = QGraphicsScene()
                video_item = QGraphicsVideoItem()
                video_item.setSize(QSizeF(360, 200))

                scene.addItem(video_item)

                graphics_view = QGraphicsView(scene)
                graphics_view.setFixedSize(360, 200)
                graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                graphics_view.setStyleSheet("""
                    QGraphicsView { 
                        background: transparent; 
                        border: none; 
                        border-radius: 6px;
                    }
                """)

                layout.addWidget(graphics_view)

                player = QMediaPlayer()
                player.setVideoOutput(video_item)
                player.setMedia(QMediaContent(QUrl.fromLocalFile(temp_video.name)))
                player.setVolume(50)

                control_panel = QWidget()
                control_panel.setStyleSheet("""
                    QWidget { 
                        background: rgba(0, 0, 0, 0.3); 
                        border-radius: 6px;
                    }
                """)
                control_layout = QHBoxLayout(control_panel)
                control_layout.setContentsMargins(6, 4, 6, 4)
                control_layout.setSpacing(6)

                play_btn = QToolButton()
                play_btn.setIcon(play_btn.style().standardIcon(QStyle.SP_MediaPlay))
                play_btn.setStyleSheet("""
                    QToolButton { 
                        background: transparent; 
                        border: none; 
                        color: #cccccc;
                        padding: 4px;
                    }
                    QToolButton:hover {
                        color: #ffffff;
                    }
                """)

                def toggle_play():
                    if player.state() == QMediaPlayer.PlayingState:
                        player.pause()
                    else:
                        player.play()

                play_btn.clicked.connect(toggle_play)

                progress_slider = QSlider(Qt.Horizontal)
                progress_slider.setRange(0, 0)
                progress_slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        border: none;
                        height: 3px;
                        background: #555555;
                        border-radius: 1px;
                    }
                    QSlider::handle:horizontal {
                        background: #cccccc;
                        border: none;
                        width: 10px;
                        height: 10px;
                        border-radius: 5px;
                        margin: -4px 0;
                    }
                    QSlider::sub-page:horizontal {
                        background: #888888;
                        border-radius: 1px;
                    }
                """)

                def update_slider(position):
                    progress_slider.setValue(position)

                def update_duration(duration):
                    progress_slider.setRange(0, duration)

                def set_position(position):
                    player.setPosition(position)

                player.positionChanged.connect(update_slider)
                player.durationChanged.connect(update_duration)
                progress_slider.sliderMoved.connect(set_position)

                volume_slider = QSlider(Qt.Horizontal)
                volume_slider.setRange(0, 100)
                volume_slider.setValue(50)
                volume_slider.setFixedWidth(80)
                volume_slider.setStyleSheet("""
                    QSlider::groove:horizontal {
                        border: none;
                        height: 3px;
                        background: #555555;
                        border-radius: 1px;
                    }
                    QSlider::handle:horizontal {
                        background: #cccccc;
                        border: none;
                        width: 8px;
                        height: 8px;
                        border-radius: 4px;
                        margin: -3px 0;
                    }
                    QSlider::sub-page:horizontal {
                        background: #888888;
                        border-radius: 1px;
                    }
                """)
                volume_slider.valueChanged.connect(player.setVolume)

                vol_label = QLabel("Vol:")
                vol_label.setStyleSheet("""
                    QLabel { 
                        color: #cccccc; 
                        font-size: 10px; 
                        background: transparent;
                        padding: 0 4px;
                    }
                """)

                control_layout.addWidget(play_btn)
                control_layout.addWidget(progress_slider)
                control_layout.addWidget(vol_label)
                control_layout.addWidget(volume_slider)

                layout.addWidget(control_panel)

                def update_icon(state):
                    if state == QMediaPlayer.PlayingState:
                        play_btn.setIcon(play_btn.style().standardIcon(QStyle.SP_MediaPause))
                    else:
                        play_btn.setIcon(play_btn.style().standardIcon(QStyle.SP_MediaPlay))

                player.stateChanged.connect(update_icon)

                def handle_media_status(status):
                    if status == QMediaPlayer.EndOfMedia:
                        player.pause()
                        player.setPosition(0)
                        update_icon(QMediaPlayer.PausedState)

                player.mediaStatusChanged.connect(handle_media_status)

                graphics_view.player = player
                graphics_view.temp_path = temp_video.name

                player.pause()
                player.setPosition(0)
            else:
                add_file_row()

            save_button = QPushButton("Save File")
            save_button.setStyleSheet("""
                QPushButton {
                    background-color: #3a5a7a;
                    color: #ffffff;
                    border: 1px solid #4a6a8a;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-size: 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #4a6a8a;
                    border-color: #5a7a9a;
                }
                QPushButton:pressed {
                    background-color: #2a4a6a;
                }
            """)

            def save_file():
                path, _ = QFileDialog.getSaveFileName(self, "Save File", file_name or "download")
                if path:
                    with open(path, "wb") as f:
                        f.write(file_bytes)

            save_button.clicked.connect(save_file)
            layout.addWidget(save_button)
        else:
            message_text = QTextEdit()
            message_text.setReadOnly(True)
            message_text.setHtml(
                f"<div style='color: #eeeeee; font-size: 13px; line-height: 1.4;'>"
                f"{text}"
                f"</div>"
            )
            message_text.setStyleSheet("""
                QTextEdit {
                    background: transparent;
                    border: none;
                    padding: 0;
                    font-size: 13px;
                }
            """)
            message_text.setWordWrapMode(QTextOption.WrapAnywhere)
            message_text.setMaximumWidth(260)
            message_text.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

            document = message_text.document()
            document.setTextWidth(260)
            height = document.size().height()
            message_text.setFixedHeight(int(height + 2))

            layout.addWidget(message_text)

        wrapper = QWidget()
        wrapper.setStyleSheet("QWidget { background: transparent; }")
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(15, 5, 15, 5)
        wrapper_layout.setAlignment(Qt.AlignRight if is_own else Qt.AlignLeft)

        if is_own:
            wrapper_layout.addStretch(1)
            wrapper_layout.addWidget(bubble, 0)
            wrapper_layout.addSpacing(10)
        else:
            wrapper_layout.addSpacing(10)
            wrapper_layout.addWidget(bubble, 0)
            wrapper_layout.addStretch(1)

        self.messages_layout.insertWidget(self.messages_layout.count() - 1, wrapper)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def append_system_message(self, text: str):
        label = QLabel(f"<div style='text-align:center; color: #aaaaaa; font-size: 11px;'><i>{text}</i></div>")
        label.setTextFormat(Qt.RichText)
        label.setAlignment(Qt.AlignCenter)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, label)
        self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum())

    def show_progress(self, title="Processing..."):
        self.progress_bar.setFormat(f"{title} - %p%")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)
        self.message_input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.attach_button.setEnabled(False)

    def update_progress(self, value: int):
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(value)

    def hide_progress(self):
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        self.progress_bar.setValue(0)
        self.message_input.setEnabled(True)
        self.set_send_button_state(self.is_encryption_ready)