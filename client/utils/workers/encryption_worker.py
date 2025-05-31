import logging
import base64
from PyQt5.QtCore import QThread, pyqtSignal

from crypto.base.modes import PaddingMode, CipherMode

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SecureChat")

class EncryptionWorker(QThread):

    progress = pyqtSignal(int)
    result = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, crypto_manager, algorithm, key, data, 
                 mode=CipherMode.CBC, padding_mode=PaddingMode.PKCS7, parent=None):
        super().__init__(parent)
        self.crypto_manager = crypto_manager
        self.algorithm = algorithm
        self.key = key
        self.data = data
        self.mode = mode
        self.padding_mode = padding_mode
        self._is_running = False
        self._cancelled = False

    def run(self):
        self._is_running = True
        self._cancelled = False
        
        try:
            if not isinstance(self.data, bytes):
                raise TypeError("Data to encrypt must be bytes")
            
            def report_progress(percent):
                if self._cancelled:
                    raise Exception("cancelled")
                self.progress.emit(percent)

            ciphertext, iv = self.crypto_manager.encrypt(
                algorithm=self.algorithm,
                key=self.key,
                plaintext=self.data,
                mode=self.mode,
                padding_mode=self.padding_mode,
                progress_callback=report_progress
            )

            encrypted_base64 = base64.b64encode(ciphertext).decode('utf-8')
            iv_base64 = base64.b64encode(iv).decode('utf-8')
            
            self.result.emit((encrypted_base64, iv_base64))

        except Exception as e:
            logger.exception("Encryption error:")
            self.error.emit(f"Encryption error: {str(e)}")
        finally:
            self._is_running = False

    def cancel(self):
        if self._is_running:
            self._cancelled = True
            self.quit()
            self.wait()
            logger.info("Encryption cancellation requested.")
