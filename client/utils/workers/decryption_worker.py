import time
import logging
import base64
from PyQt5.QtCore import QThread, pyqtSignal

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SecretChat")

class DecryptionWorker(QThread):

    progress = pyqtSignal(int)
    result = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, crypto_manager, algorithm, key, encrypted_data_b64, iv_b64,
                 mode, padding_mode, parent=None):
        super().__init__(parent)
        self.crypto_manager = crypto_manager
        self.algorithm = algorithm
        self.key = key
        self.encrypted_data_b64 = encrypted_data_b64
        self.iv_b64 = iv_b64
        self.mode = mode
        self.padding_mode = padding_mode
        self.cancelled = False
        self._is_running = False

    def run(self):
        self._is_running = True
        self.cancelled = False
        try:
            encrypted_bytes = base64.b64decode(self.encrypted_data_b64)
            iv_bytes = base64.b64decode(self.iv_b64)

            def report_progress(percent):
                if self.cancelled:
                    raise Exception("cancelled")
                self.progress.emit(percent)

            decrypted_data = self.crypto_manager.decrypt(
                self.algorithm,
                self.key,
                encrypted_bytes,
                mode=self.mode,
                padding_mode=self.padding_mode,
                iv=None,
                progress_callback=report_progress
            )

            self.result.emit(decrypted_data)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self._is_running = False

    def cancel(self):
        if self._is_running:
            self.cancelled = True
            self.quit()
            self.wait()
            logger.info("Decryption cancellation requested.")
