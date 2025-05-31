import os
from typing import Optional, Callable
from cryptography.hazmat.backends import default_backend

from crypto.base.modes import PaddingMode, CipherMode
from crypto.symmetric.mac_guffin import MacGuffinCipher
from crypto.symmetric.serpent import SerpentCipher
from utils.constants import EncryptionAlgorithm

class CryptographyManager:
    
    def __init__(self):
        self.backend = default_backend()

    def generate_iv(self, block_size=8):
        return os.urandom(block_size)

    def encrypt(self, algorithm: EncryptionAlgorithm, key: bytes, plaintext: bytes, 
                mode: CipherMode = CipherMode.CBC, padding_mode: PaddingMode = PaddingMode.PKCS7,
                iv: bytes = None, progress_callback: Optional[Callable[[int], None]] = None) -> tuple:
        if algorithm == EncryptionAlgorithm.MACGUFFIN:
            return self._encrypt_macguffin(
                key,
                plaintext,
                mode,
                padding_mode,
                iv,
                progress_callback
            )
        elif algorithm == EncryptionAlgorithm.SERPENT:
            return self._encrypt_serpent(
                key,
                plaintext,
                mode,
                padding_mode,
                iv,
                progress_callback
            )
        else:
            raise ValueError(f"Encryption not implemented for {algorithm}")

    def decrypt(self, algorithm: EncryptionAlgorithm, key: bytes, ciphertext: bytes, 
                mode: CipherMode = CipherMode.CBC, padding_mode: PaddingMode = PaddingMode.PKCS7,
                iv: bytes = None, progress_callback: Optional[Callable[[int], None]] = None) -> bytes:     
        if algorithm == EncryptionAlgorithm.MACGUFFIN:
            return self._decrypt_macguffin(
                key,
                ciphertext,
                mode,
                padding_mode,
                iv,
                progress_callback
            )
        elif algorithm == EncryptionAlgorithm.SERPENT:
            return self._decrypt_serpent(
                key,
                ciphertext,
                mode,
                padding_mode,
                iv,
                progress_callback
            )
        else:
            raise ValueError(f"Decryption not implemented for {algorithm}")

    def _encrypt_macguffin(self, key: bytes, plaintext: bytes, mode: CipherMode,
                     padding_mode: PaddingMode, iv: bytes = None, progress_callback: Optional[Callable[[int], None]] = None) -> tuple:
        if iv is None:
            iv = self.generate_iv(8)
        cipher = MacGuffinCipher(key)
        ciphertext = cipher.encrypt(
            plaintext,
            mode=mode,
            iv=iv,
            padding=padding_mode,
            progress_callback=progress_callback
        )
        
        return ciphertext, iv

    def _decrypt_macguffin(self, key: bytes, ciphertext: bytes, mode: CipherMode,
                     padding_mode: PaddingMode, iv: bytes, progress_callback: Optional[Callable[[int], None]] = None) -> bytes:
        cipher = MacGuffinCipher(key)
        plaintext = cipher.decrypt(
            ciphertext,
            mode=mode,
            iv=iv,
            padding=padding_mode,
            progress_callback=progress_callback
        )
        
        return plaintext

    def _encrypt_serpent(self, key: bytes, plaintext: bytes, mode: CipherMode,
                         padding_mode: PaddingMode, iv: bytes = None, progress_callback: Optional[Callable[[int], None]] = None) -> tuple:
        if iv is None:
            iv = self.generate_iv(16)
        cipher = SerpentCipher(key)
        ciphertext = cipher.encrypt(
            plaintext,
            mode=mode,
            iv=iv,
            padding=padding_mode,
            progress_callback=progress_callback
        )
        
        return ciphertext, iv

    def _decrypt_serpent(self, key: bytes, ciphertext: bytes, mode: CipherMode,
                         padding_mode: PaddingMode, iv: bytes, progress_callback: Optional[Callable[[int], None]] = None) -> bytes:
        cipher = SerpentCipher(key)
        plaintext = cipher.decrypt(
            ciphertext,
            mode=mode,
            iv=iv,
            padding=padding_mode,
            progress_callback=progress_callback
        )
        
        return plaintext
