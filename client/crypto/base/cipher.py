from abc import ABC, abstractmethod
from typing import Optional, Callable
import os
import sys
import time
from colorama import Fore, Style, init
from crypto.base.modes import PaddingMode, CipherMode

init()


class SymmetricCipher(ABC):
    """🔒 Базовый класс для симметричных шифров с улучшенным визуальным оформлением"""

    ALLOWED_KEY_SIZES = [16]

    def __init__(self, key: bytes):
        self._print_banner()
        self._validate_key(key)
        self.key = key
        self._print_success(f"Инициализирован шифр с ключом: {self._format_key(key)}")

    def _print_banner(self):
        """Выводит стилизованный заголовок"""
        print(Fore.BLUE + "╔════════════════════════════════════════╗")
        print(Fore.BLUE + "║" + Fore.CYAN + "       СИММЕТРИЧНЫЙ ШИФР       " + Fore.BLUE + "     ║")
        print(Fore.BLUE + "╚════════════════════════════════════════╝" + Style.RESET_ALL)

    def _print_success(self, message: str):
        """Выводит сообщение об успехе"""
        print(Fore.GREEN + "✓ " + message + Style.RESET_ALL)

    def _print_warning(self, message: str):
        """Выводит предупреждение"""
        print(Fore.YELLOW + "⚠ " + message + Style.RESET_ALL)

    def _print_error(self, message: str):
        """Выводит сообщение об ошибке"""
        print(Fore.RED + "✗ " + message + Style.RESET_ALL)

    def _format_key(self, key: bytes) -> str:
        """Форматирует ключ для красивого вывода"""
        return " ".join(f"{b:02x}" for b in key)

    def _animate_loading(self, message: str):
        """Анимация загрузки"""
        print(Fore.MAGENTA + "⌛ " + message + Style.RESET_ALL, end='')
        sys.stdout.flush()
        for _ in range(3):
            time.sleep(0.3)
            print(".", end='')
            sys.stdout.flush()
        print()

    def _validate_key(self, key: bytes):
        """Валидация ключа с визуальным оформлением"""
        self._animate_loading("Проверка ключа")

        if len(key) not in self.ALLOWED_KEY_SIZES:
            self._print_error(f"Неверный размер ключа: {len(key)} байт. Допустимые: {self.ALLOWED_KEY_SIZES}")
            raise ValueError(f"Invalid key size: {len(key)} bytes. Allowed: {self.ALLOWED_KEY_SIZES}")

        if all(b == 0 for b in key):
            self._print_error("Обнаружен слабый ключ: нулевые байты не допускаются")
            raise ValueError("Weak key detected: all-zero bytes are not allowed.")

        self._print_success("Ключ прошел валидацию")

    def _generate_iv(self) -> bytes:
        """Генерация вектора инициализации с анимацией"""
        self._animate_loading("Генерация вектора инициализации")
        iv = os.urandom(self.BLOCK_SIZE)
        self._print_success(f"Сгенерирован IV: {self._format_key(iv)}")
        return iv

    def _pad_data(self, data: bytes, mode: PaddingMode) -> bytes:
        """Добавление padding'а с визуализацией"""
        pad_len = self.BLOCK_SIZE - (len(data) % self.BLOCK_SIZE)
        if pad_len == 0:
            pad_len = self.BLOCK_SIZE

        self._print_warning(f"Добавление padding'а ({mode.name}): {pad_len} байт")

        if mode == PaddingMode.ZEROS:
            padding = bytes([0] * pad_len)
        elif mode == PaddingMode.ANSI_X923:
            padding = bytes([0] * (pad_len - 1) + [pad_len])
        elif mode == PaddingMode.PKCS7:
            padding = bytes([pad_len] * pad_len)
        elif mode == PaddingMode.ISO_10126:
            padding = os.urandom(pad_len - 1) + bytes([pad_len])
        else:
            self._print_error(f"Неизвестный режим padding'а: {mode}")
            raise ValueError(f"Unknown padding mode: {mode}")

        return data + padding

    def _unpad_data(self, data: bytes, mode: PaddingMode) -> bytes:
        """Удаление padding'а с визуализацией"""
        if len(data) == 0:
            return b''

        if len(data) % self.BLOCK_SIZE != 0:
            self._print_error(f"Некорректная длина данных для удаления padding'а")
            raise ValueError("Invalid data length for removing padding")

        self._print_warning(f"Удаление padding'а ({mode.name})")

        if mode == PaddingMode.ZEROS:
            i = len(data) - 1
            while i >= 0 and data[i] == 0:
                i -= 1
            return data[:i + 1] if i >= 0 else b''

        elif mode in (PaddingMode.ANSI_X923, PaddingMode.PKCS7, PaddingMode.ISO_10126):
            pad_len = data[-1]
            if pad_len == 0 or pad_len > self.BLOCK_SIZE:
                if pad_len == 0:
                    return data
                self._print_error("Некорректное значение padding'а")
                raise ValueError("Invalid padding value")

            if mode == PaddingMode.PKCS7:
                for i in range(len(data) - pad_len, len(data)):
                    if data[i] != pad_len:
                        if all(b != pad_len for b in data[-pad_len:-1]):
                            return data
                        self._print_error("Некорректный PKCS7 padding")
                        raise ValueError("Invalid PKCS7 padding")

            elif mode == PaddingMode.ANSI_X923:
                for i in range(len(data) - pad_len, len(data) - 1):
                    if data[i] != 0:
                        return data

            return data[:-pad_len]

        else:
            self._print_error(f"Неизвестный режим padding'а: {mode}")
            raise ValueError(f"Unknown padding mode: {mode}")

    def encrypt(self, data: bytes, mode: CipherMode = CipherMode.ECB,
                iv: Optional[bytes] = None, padding: PaddingMode = PaddingMode.PKCS7,
                progress_callback: Optional[Callable[[int], None]] = None) -> bytes:
        """Шифрование данных с улучшенным визуальным выводом"""
        print(Fore.CYAN + "\n🔐 Начало шифрования:" + Style.RESET_ALL)
        print(Fore.BLUE + f"Режим: {mode.name}, Padding: {padding.name}" + Style.RESET_ALL)

        if len(data) == 0:
            self._print_warning("Шифрование пустых данных")
            padded_data = self._pad_data(data, padding)
        else:
            padded_data = self._pad_data(data, padding)

        if mode != CipherMode.ECB:
            if iv is None:
                iv = self._generate_iv()
                result = bytearray(iv)
            else:
                if len(iv) != self.BLOCK_SIZE:
                    self._print_error(f"IV должен быть длиной {self.BLOCK_SIZE} байт")
                    raise ValueError(f"IV must be {self.BLOCK_SIZE} bytes long")
                result = bytearray(iv)
                self._print_success(f"Использован предоставленный IV: {self._format_key(iv)}")
        else:
            result = bytearray()

        total_blocks = len(padded_data) // self.BLOCK_SIZE
        last_progress = -1

        self._animate_loading(f"Шифрование {len(padded_data)} байт ({total_blocks} блоков)")

        if mode == CipherMode.ECB:
            for i in range(0, len(padded_data), self.BLOCK_SIZE):
                block = padded_data[i:i + self.BLOCK_SIZE]
                result.extend(self.encrypt_block(block))

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.CBC:
            prev_block = iv
            for i in range(0, len(padded_data), self.BLOCK_SIZE):
                block = padded_data[i:i + self.BLOCK_SIZE]
                xored_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    xored_block[j] = block[j] ^ prev_block[j]

                encrypted_block = self.encrypt_block(bytes(xored_block))
                result.extend(encrypted_block)
                prev_block = encrypted_block

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.PCBC:
            prev_block = iv
            for i in range(0, len(padded_data), self.BLOCK_SIZE):
                block = padded_data[i:i + self.BLOCK_SIZE]
                xored_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    xored_block[j] = block[j] ^ prev_block[j]

                encrypted_block = self.encrypt_block(bytes(xored_block))
                result.extend(encrypted_block)

                next_prev = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    next_prev[j] = block[j] ^ encrypted_block[j]
                prev_block = bytes(next_prev)

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.CFB:
            prev_block = iv
            for i in range(0, len(padded_data), self.BLOCK_SIZE):
                block = padded_data[i:i + self.BLOCK_SIZE]
                encrypted_prev = self.encrypt_block(prev_block)

                output_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    output_block[j] = block[j] ^ encrypted_prev[j]

                result.extend(output_block)
                prev_block = bytes(output_block)

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.OFB:
            register = iv
            for i in range(0, len(padded_data), self.BLOCK_SIZE):
                block = padded_data[i:i + self.BLOCK_SIZE]
                register = self.encrypt_block(register)

                output_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    output_block[j] = block[j] ^ register[j]

                result.extend(output_block)

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.CTR:
            counter = int.from_bytes(iv, byteorder='big')
            for i in range(0, len(padded_data), self.BLOCK_SIZE):
                block = padded_data[i:i + self.BLOCK_SIZE]
                counter_bytes = counter.to_bytes(self.BLOCK_SIZE, byteorder='big')

                encrypted_counter = self.encrypt_block(counter_bytes)

                output_block = bytearray(min(self.BLOCK_SIZE, len(padded_data) - i))
                for j in range(len(output_block)):
                    output_block[j] = block[j] ^ encrypted_counter[j]

                result.extend(output_block)
                counter += 1

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.RANDOM_DELTA:
            delta = iv
            for i in range(0, len(padded_data), self.BLOCK_SIZE):
                block = padded_data[i:i + self.BLOCK_SIZE]
                xored_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    xored_block[j] = block[j] ^ delta[j]

                encrypted_block = self.encrypt_block(bytes(xored_block))
                result.extend(encrypted_block)

                delta = self.encrypt_block(delta)

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        else:
            self._print_error(f"Неизвестный режим шифрования: {mode}")
            raise ValueError(f"Unknown cypher mode: {mode}")

        encrypted_data = bytes(result)
        self._print_success(f"Шифрование завершено. Результат: {len(encrypted_data)} байт")
        print(Fore.CYAN + "════════════════════════════════════════" + Style.RESET_ALL)
        return encrypted_data

    def decrypt(self, data: bytes, mode: CipherMode = CipherMode.ECB,
                iv: Optional[bytes] = None, padding: PaddingMode = PaddingMode.PKCS7,
                progress_callback: Optional[Callable[[int], None]] = None) -> bytes:
        """Дешифрование данных с улучшенным визуальным выводом"""
        print(Fore.CYAN + "\n🔓 Начало дешифрования:" + Style.RESET_ALL)
        print(Fore.BLUE + f"Режим: {mode.name}, Padding: {padding.name}" + Style.RESET_ALL)

        if len(data) == 0:
            self._print_warning("Дешифрование пустых данных")
            return b''

        if len(data) % self.BLOCK_SIZE != 0:
            self._print_error(f"Длина данных должна быть кратна {self.BLOCK_SIZE}")
            raise ValueError(f"Data length must be a multiple of {self.BLOCK_SIZE}")

        if mode != CipherMode.ECB and iv is None:
            iv = data[:self.BLOCK_SIZE]
            data = data[self.BLOCK_SIZE:]
            self._print_success(f"Извлечен IV из данных: {self._format_key(iv)}")

        result = bytearray()
        total_blocks = len(data) // self.BLOCK_SIZE
        last_progress = -1

        self._animate_loading(f"Дешифрование {len(data)} байт ({total_blocks} блоков)")

        if mode == CipherMode.ECB:
            for i in range(0, len(data), self.BLOCK_SIZE):
                block = data[i:i + self.BLOCK_SIZE]
                result.extend(self.decrypt_block(block))

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.CBC:
            prev_block = iv
            for i in range(0, len(data), self.BLOCK_SIZE):
                block = data[i:i + self.BLOCK_SIZE]
                decrypted_block = self.decrypt_block(block)

                output_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    output_block[j] = decrypted_block[j] ^ prev_block[j]

                result.extend(output_block)
                prev_block = block

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.PCBC:
            prev_block = iv
            for i in range(0, len(data), self.BLOCK_SIZE):
                block = data[i:i + self.BLOCK_SIZE]
                decrypted_block = self.decrypt_block(block)

                output_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    output_block[j] = decrypted_block[j] ^ prev_block[j]

                result.extend(output_block)

                next_prev = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    next_prev[j] = output_block[j] ^ block[j]
                prev_block = bytes(next_prev)

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.CFB:
            prev_block = iv
            for i in range(0, len(data), self.BLOCK_SIZE):
                block = data[i:i + self.BLOCK_SIZE]
                encrypted_prev = self.encrypt_block(prev_block)

                output_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    output_block[j] = block[j] ^ encrypted_prev[j]

                result.extend(output_block)
                prev_block = block

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.OFB:
            register = iv
            for i in range(0, len(data), self.BLOCK_SIZE):
                block = data[i:i + self.BLOCK_SIZE]
                register = self.encrypt_block(register)

                output_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    output_block[j] = block[j] ^ register[j]

                result.extend(output_block)

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.CTR:
            counter = int.from_bytes(iv, byteorder='big')
            for i in range(0, len(data), self.BLOCK_SIZE):
                block = data[i:i + self.BLOCK_SIZE]
                counter_bytes = counter.to_bytes(self.BLOCK_SIZE, byteorder='big')

                encrypted_counter = self.encrypt_block(counter_bytes)

                output_block = bytearray(len(block))
                for j in range(len(output_block)):
                    output_block[j] = block[j] ^ encrypted_counter[j]

                result.extend(output_block)
                counter += 1

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        elif mode == CipherMode.RANDOM_DELTA:
            delta = iv
            for i in range(0, len(data), self.BLOCK_SIZE):
                block = data[i:i + self.BLOCK_SIZE]
                decrypted_block = self.decrypt_block(block)

                output_block = bytearray(self.BLOCK_SIZE)
                for j in range(self.BLOCK_SIZE):
                    output_block[j] = decrypted_block[j] ^ delta[j]

                result.extend(output_block)

                delta = self.encrypt_block(delta)

                if progress_callback:
                    block_num = i // self.BLOCK_SIZE + 1
                    progress = int(block_num / total_blocks * 100)
                    if progress != last_progress:
                        progress_callback(progress)
                        last_progress = progress

        else:
            self._print_error(f"Неизвестный режим шифрования: {mode}")
            raise ValueError(f"Unknown cypher mode: {mode}")

        decrypted_data = self._unpad_data(bytes(result), padding)
        self._print_success(f"Дешифрование завершено. Результат: {len(decrypted_data)} байт")
        print(Fore.CYAN + "════════════════════════════════════════" + Style.RESET_ALL)
        return decrypted_data

    @abstractmethod
    def encrypt_block(self, plaintext: bytes) -> bytes:
        pass

    @abstractmethod
    def decrypt_block(self, ciphertext: bytes) -> bytes:
        pass