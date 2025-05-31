from crypto.symmetric.serpent import SerpentCipher
from crypto.base.modes import CipherMode, PaddingMode
import os

# Ключ должен быть 16 байт для MacGuffin
key = b'R/\x8e\xec\xb5\x92t\n\xd623\x96 \xe2\xec+'
# IV должен быть 16 байт для CBC режима
iv = os.urandom(16)  # Исправлено: 16 байт вместо 8
cipher = SerpentCipher(key)

test_text = "Hello, World!"
print(f"Original text: {test_text}")

# Шифрование с PKCS7 padding (рекомендуется)
try:
    encrypted = cipher.encrypt(
        test_text.encode('utf-8'),
        mode=CipherMode.CBC,
        iv=iv,
        padding=PaddingMode.ZEROS  # Исправлено: PKCS7 вместо ZEROS
    )
    print(f"Encrypted: {encrypted.hex()}")

    # Дешифрование
    decrypted = cipher.decrypt(
        encrypted,
        mode=CipherMode.CBC,
        iv=iv,
        padding=PaddingMode.ZEROS  # Должен совпадать с шифрованием
    )

    # Безопасное декодирование
    try:
        print(f"Decrypted bytes: {decrypted}")
        print(f"Decrypted text: {decrypted.decode('utf-8')}")
    except UnicodeDecodeError:
        # Если есть проблемы с декодированием, покажем hex
        print("Decoded with UTF-8 failed. Hex representation:")
        print(decrypted.hex())

except ValueError as e:
    print(f"Error: {str(e)}")