from crypto.base.cipher import SymmetricCipher
import logging
import struct
from abc import ABC, abstractmethod
from typing import Optional, Callable
import os

# Константы
PHI = 0x9E3779B9  # Константа золотого сечения (sqrt(5) - 1) * 2**31
BLOCK_SIZE = 16  # Размер блока в байтах


class SerpentCipher(SymmetricCipher):
    ALLOWED_KEY_SIZES = [16, 24, 32]  # Поддерживаемые размеры ключей: 128, 192, 256 бит
    PHI = 0x9E3779B9  # Константа золотого сечения (sqrt(5) - 1) * 2**31
    BLOCK_SIZE = 16  # Размер блока в байтах
    def __init__(self, key: bytes):
        self._validate_key(key)
        self.key = key
        self.subkeys = self._key_schedule(key)

    def _key_schedule(self, key: bytes) -> list:
        # Преобразование ключа в массив 32-битных слов
        k = [0] * 16
        for i in range(0, len(key), 4):
            k[i // 4] = int.from_bytes(key[i:i + 4], byteorder='little')

        # Если ключ меньше 256 бит, дополняем его
        if len(key) < 32:
            k[len(key) // 4] = 1

        # Генерация промежуточных ключей
        for i in range(8, 16):
            x = k[i - 8] ^ k[i - 5] ^ k[i - 3] ^ k[i - 1] ^ PHI ^ (i - 8)
            k[i] = ((x << 11) | (x >> 21)) & 0xFFFFFFFF

        # Инициализация массива подключей
        subkeys = [0] * 132

        # Первые 8 подключа
        for i in range(8, 16):
            subkeys[i - 8] = k[i]

        # Генерация остальных подключа
        for i in range(8, 132):
            x = subkeys[i - 8] ^ subkeys[i - 5] ^ subkeys[i - 3] ^ subkeys[i - 1] ^ PHI ^ i
            subkeys[i] = ((x << 11) | (x >> 21)) & 0xFFFFFFFF

        # Применение S-блоков к подключам
        for i in range(0, 132, 4):
            if i + 3 >= 132:
                break

            # Выбор S-блока в зависимости от позиции
            sbox_num = (i // 4) % 8
            if sbox_num == 0:
                self._apply_sb3(subkeys, i, i + 1, i + 2, i + 3)
            elif sbox_num == 1:
                self._apply_sb2(subkeys, i, i + 1, i + 2, i + 3)
            elif sbox_num == 2:
                self._apply_sb1(subkeys, i, i + 1, i + 2, i + 3)
            elif sbox_num == 3:
                self._apply_sb0(subkeys, i, i + 1, i + 2, i + 3)
            elif sbox_num == 4:
                self._apply_sb7(subkeys, i, i + 1, i + 2, i + 3)
            elif sbox_num == 5:
                self._apply_sb6(subkeys, i, i + 1, i + 2, i + 3)
            elif sbox_num == 6:
                self._apply_sb5(subkeys, i, i + 1, i + 2, i + 3)
            elif sbox_num == 7:
                self._apply_sb4(subkeys, i, i + 1, i + 2, i + 3)

        return subkeys

    def encrypt_block(self, plaintext: bytes) -> bytes:
        if len(plaintext) != BLOCK_SIZE:
            raise ValueError(f"Plaintext must be {BLOCK_SIZE} bytes long")

        # Преобразование входного блока в 4 32-битных слова
        r0 = int.from_bytes(plaintext[0:4], byteorder='little')
        r1 = int.from_bytes(plaintext[4:8], byteorder='little')
        r2 = int.from_bytes(plaintext[8:12], byteorder='little')
        r3 = int.from_bytes(plaintext[12:16], byteorder='little')

        # Начальное преобразование
        r0 ^= self.subkeys[0]
        r1 ^= self.subkeys[1]
        r2 ^= self.subkeys[2]
        r3 ^= self.subkeys[3]

        # 32 раунда
        for i in range(0, 128, 4):
            # Применение S-блока
            sbox_num = (i // 4) % 8
            if sbox_num == 0:
                self._sb0(r0, r1, r2, r3)
            elif sbox_num == 1:
                self._sb1(r0, r1, r2, r3)
            elif sbox_num == 2:
                self._sb2(r0, r1, r2, r3)
            elif sbox_num == 3:
                self._sb3(r0, r1, r2, r3)
            elif sbox_num == 4:
                self._sb4(r0, r1, r2, r3)
            elif sbox_num == 5:
                self._sb5(r0, r1, r2, r3)
            elif sbox_num == 6:
                self._sb6(r0, r1, r2, r3)
            elif sbox_num == 7:
                self._sb7(r0, r1, r2, r3)

            # Линейное преобразование
            self._linear(r0, r1, r2, r3)

            # Добавление подключа
            r0 ^= self.subkeys[i + 4]
            r1 ^= self.subkeys[i + 5]
            r2 ^= self.subkeys[i + 6]
            r3 ^= self.subkeys[i + 7]

        # Финальное преобразование
        r0 ^= self.subkeys[128]
        r1 ^= self.subkeys[129]
        r2 ^= self.subkeys[130]
        r3 ^= self.subkeys[131]

        # Сборка зашифрованного блока
        return (r0.to_bytes(4, byteorder='little') +
                r1.to_bytes(4, byteorder='little') +
                r2.to_bytes(4, byteorder='little') +
                r3.to_bytes(4, byteorder='little'))

    def decrypt_block(self, ciphertext: bytes) -> bytes:
        if len(ciphertext) != BLOCK_SIZE:
            raise ValueError(f"Ciphertext must be {BLOCK_SIZE} bytes long")

        # Преобразование входного блока в 4 32-битных слова
        r0 = int.from_bytes(ciphertext[0:4], byteorder='little')
        r1 = int.from_bytes(ciphertext[4:8], byteorder='little')
        r2 = int.from_bytes(ciphertext[8:12], byteorder='little')
        r3 = int.from_bytes(ciphertext[12:16], byteorder='little')

        # Начальное преобразование
        r0 ^= self.subkeys[128]
        r1 ^= self.subkeys[129]
        r2 ^= self.subkeys[130]
        r3 ^= self.subkeys[131]

        # 32 раунда в обратном порядке
        for i in range(124, -4, -4):
            # Применение обратного S-блока
            sbox_num = ((i + 4) // 4) % 8
            if sbox_num == 0:
                self._sb0_inv(r0, r1, r2, r3)
            elif sbox_num == 1:
                self._sb1_inv(r0, r1, r2, r3)
            elif sbox_num == 2:
                self._sb2_inv(r0, r1, r2, r3)
            elif sbox_num == 3:
                self._sb3_inv(r0, r1, r2, r3)
            elif sbox_num == 4:
                self._sb4_inv(r0, r1, r2, r3)
            elif sbox_num == 5:
                self._sb5_inv(r0, r1, r2, r3)
            elif sbox_num == 6:
                self._sb6_inv(r0, r1, r2, r3)
            elif sbox_num == 7:
                self._sb7_inv(r0, r1, r2, r3)

            # Обратное линейное преобразование
            self._linear_inv(r0, r1, r2, r3)

            # Добавление подключа
            r0 ^= self.subkeys[i + 4]
            r1 ^= self.subkeys[i + 5]
            r2 ^= self.subkeys[i + 6]
            r3 ^= self.subkeys[i + 7]

        # Финальное преобразование
        r0 ^= self.subkeys[0]
        r1 ^= self.subkeys[1]
        r2 ^= self.subkeys[2]
        r3 ^= self.subkeys[3]

        # Сборка расшифрованного блока
        return (r0.to_bytes(4, byteorder='little') +
                r1.to_bytes(4, byteorder='little') +
                r2.to_bytes(4, byteorder='little') +
                r3.to_bytes(4, byteorder='little'))

    # Линейное преобразование
    def _linear(self, r0, r1, r2, r3):
        t0 = ((r0 << 13) | (r0 >> (32 - 13))) & 0xFFFFFFFF
        t2 = ((r2 << 3) | (r2 >> (32 - 3))) & 0xFFFFFFFF
        t1 = r1 ^ t0 ^ t2
        t3 = r3 ^ t2 ^ ((t0 << 3) & 0xFFFFFFFF)
        r1 = ((t1 << 1) | (t1 >> (32 - 1))) & 0xFFFFFFFF
        r3 = ((t3 << 7) | (t3 >> (32 - 7))) & 0xFFFFFFFF
        t0 = t0 ^ r1 ^ r3
        t2 = t2 ^ r3 ^ ((r1 << 7) & 0xFFFFFFFF)
        r0 = ((t0 << 5) | (t0 >> (32 - 5))) & 0xFFFFFFFF
        r2 = ((t2 << 22) | (t2 >> (32 - 22))) & 0xFFFFFFFF

    # Обратное линейное преобразование
    def _linear_inv(self, r0, r1, r2, r3):
        t2 = ((r2 >> 22) | (r2 << (32 - 22))) & 0xFFFFFFFF
        t0 = ((r0 >> 5) | (r0 << (32 - 5))) & 0xFFFFFFFF
        t2 = t2 ^ r3 ^ ((r1 << 7) & 0xFFFFFFFF)
        t0 = t0 ^ r1 ^ r3
        t3 = ((r3 >> 7) | (r3 << (32 - 7))) & 0xFFFFFFFF
        t1 = ((r1 >> 1) | (r1 << (32 - 1))) & 0xFFFFFFFF
        r3 = (t3 ^ t2 ^ ((t0 << 3) & 0xFFFFFFFF)) & 0xFFFFFFFF
        r1 = (t1 ^ t0 ^ t2) & 0xFFFFFFFF
        r2 = ((t2 >> 3) | (t2 << (32 - 3))) & 0xFFFFFFFF
        r0 = ((t0 >> 13) | (t0 << (32 - 13))) & 0xFFFFFFFF

    # S-блоки и их обратные версии
    def _sb0(self, r0, r1, r2, r3):
        t0 = r0 ^ r3
        t1 = r2 ^ t0
        t2 = r1 ^ t1
        r3 = (r0 & r3) ^ t2
        t3 = r0 ^ (r1 & t0)
        r2 = t2 ^ (r2 | t3)
        t4 = r3 & (t1 ^ t3)
        r1 = (~t1) ^ t4
        r0 = t4 ^ (~t3)

    def _sb0_inv(self, r0, r1, r2, r3):
        t0 = ~r0
        t1 = r0 ^ r1
        t2 = r3 ^ (t0 | t1)
        t3 = r2 ^ t2
        r2 = t1 ^ t3
        t4 = t0 ^ (r3 & t1)
        r1 = t2 ^ (r2 & t4)
        r3 = (r0 & t2) ^ (t3 | r1)
        r0 = r3 ^ (t3 ^ t4)

    def _sb1(self, r0, r1, r2, r3):
        t0 = r1 ^ (~r0)
        t1 = r2 ^ (r0 | t0)
        r2 = r3 ^ t1
        t2 = r1 ^ (r3 | t0)
        t3 = t0 ^ r2
        r3 = t3 ^ (t1 & t2)
        t4 = t1 ^ t2
        r1 = r3 ^ t4
        r0 = t1 ^ (t3 & t4)

    def _sb1_inv(self, r0, r1, r2, r3):
        t0 = r1 ^ r3
        t1 = r0 ^ (r1 & t0)
        t2 = t0 ^ t1
        r3 = r2 ^ t2
        t3 = r1 ^ (t0 & t1)
        t4 = r3 | t3
        r1 = t1 ^ t4
        t5 = ~r1
        t6 = r3 ^ t3
        r0 = t5 ^ t6
        r2 = t2 ^ (t5 | t6)

    def _sb2(self, r0, r1, r2, r3):
        t0 = ~r0
        t1 = r1 ^ r3
        t2 = r2 & t0
        r0 = t1 ^ t2
        t3 = r2 ^ t0
        t4 = r2 ^ r0
        t5 = r1 & t4
        r3 = t3 ^ t5
        r2 = r0 ^ ((r3 | t5) & (r0 | t3))
        r1 = (t1 ^ r3) ^ (r2 ^ (r3 | t0))

    def _sb2_inv(self, r0, r1, r2, r3):
        t0 = r1 ^ r3
        t1 = ~t0
        t2 = r0 ^ r2
        t3 = r2 ^ t0
        t4 = r1 & t3
        r0 = t2 ^ t4
        t5 = r0 | t1
        t6 = r3 ^ t5
        t7 = t2 | t6
        r3 = t0 ^ t7
        t8 = ~t3
        t9 = r0 | r3
        r1 = t8 ^ t9
        r2 = (r3 & t8) ^ (t2 ^ t9)

    def _sb3(self, r0, r1, r2, r3):
        t0 = r0 ^ r1
        t1 = r0 & r2
        t2 = r0 | r3
        t3 = r2 ^ r3
        t4 = t0 & t2
        t5 = t1 | t4
        r2 = t3 ^ t5
        t6 = r1 ^ t2
        t7 = t5 ^ t6
        t8 = t3 & t7
        r0 = t0 ^ t8
        t9 = r2 & r0
        r1 = t7 ^ t9
        r3 = (r1 | r3) ^ (t3 ^ t9)

    def _sb3_inv(self, r0, r1, r2, r3):
        t0 = r0 | r1
        t1 = r1 ^ r2
        t2 = r1 & t1
        t3 = r0 ^ t2
        t4 = r2 ^ t3
        t5 = r3 | t3
        r0 = t1 ^ t5
        t6 = t1 | t5
        t7 = r3 ^ t6
        r2 = t4 ^ t7
        t8 = t0 ^ t7
        t9 = r0 & t8
        r3 = t3 ^ t9
        r1 = r3 ^ (r0 ^ t8)

    def _sb4(self, r0, r1, r2, r3):
        t0 = r0 ^ r3
        t1 = r3 & t0
        t2 = r2 ^ t1
        t3 = r1 | t2
        r3 = t0 ^ t3
        t4 = ~r1
        t5 = t0 | t4
        r0 = t2 ^ t5
        t6 = r0 & r0
        t7 = t0 ^ t4
        t8 = t3 & t7
        r2 = t6 ^ t8
        r1 = (r0 ^ t2) ^ (t7 & r2)

    def _sb4_inv(self, r0, r1, r2, r3):
        t0 = r2 | r3
        t1 = r0 & t0
        t2 = r1 ^ t1
        t3 = r0 & t2
        t4 = r2 ^ t3
        r1 = r3 ^ t4
        t5 = ~r0
        t6 = t4 & r1
        r3 = t2 ^ t6
        t7 = r1 | t5
        t8 = r3 ^ t7
        r0 = r3 ^ t8
        r2 = (t2 & t8) ^ (r1 ^ t5)

    def _sb5(self, r0, r1, r2, r3):
        t0 = ~r0
        t1 = r0 ^ r1
        t2 = r0 ^ r3
        t3 = r2 ^ t0
        t4 = t1 | t2
        r0 = t3 ^ t4
        t5 = r3 & r0
        t6 = t1 ^ r0
        r1 = t5 ^ t6
        t7 = t0 | r0
        t8 = t1 | t5
        t9 = t2 ^ t7
        r2 = t8 ^ t9
        r3 = (r1 ^ t5) ^ (r1 & t9)

    def _sb5_inv(self, r0, r1, r2, r3):
        t0 = ~r2
        t1 = r1 & t0
        t2 = r3 ^ t1
        t3 = r0 & t2
        t4 = r1 ^ t0
        r3 = t3 ^ t4
        t5 = r1 | r3
        t6 = r0 & t5
        r1 = t2 ^ t6
        t7 = r0 | r3
        t8 = t0 ^ t5
        r0 = t7 ^ t8
        r2 = (r1 & t7) ^ (t3 | (r0 ^ r2))

    def _sb6(self, r0, r1, r2, r3):
        t0 = ~r0
        t1 = r0 ^ r3
        t2 = r1 ^ t1
        t3 = t0 | t1
        t4 = r2 ^ t3
        r1 = r1 ^ t4
        t5 = t1 | r1
        t6 = r3 ^ t5
        t7 = t4 & t6
        r2 = t2 ^ t7
        t8 = t4 ^ t6
        r0 = r2 ^ t8
        r3 = (~t4) ^ (t2 & t8)

    def _sb6_inv(self, r0, r1, r2, r3):
        t0 = ~r0
        t1 = r0 ^ r1
        t2 = r2 ^ t1
        t3 = r2 | t0
        t4 = r3 ^ t3
        r1 = t2 ^ t4
        t5 = t2 & t4
        t6 = t1 ^ t5
        t7 = r1 | t6
        r3 = t4 ^ t7
        t8 = r1 | r3
        r0 = t6 ^ t8
        r2 = (r3 & t0) ^ (t2 ^ t8)

    def _sb7(self, r0, r1, r2, r3):
        t0 = r1 ^ r2
        t1 = r2 & t0
        t2 = r3 ^ t1
        t3 = r0 ^ t2
        t4 = r3 | t0
        t5 = t3 & t4
        r1 = r1 ^ t5
        t6 = t2 | r1
        t7 = r0 & t3
        r3 = t0 ^ t7
        t8 = t3 ^ t6
        t9 = r3 & t8
        r2 = t2 ^ t9
        r0 = (~t8) ^ (r3 & r2)

    def _sb7_inv(self, r0, r1, r2, r3):
        t0 = r2 | (r0 & r1)
        t1 = r3 & (r0 | r1)
        r3 = t0 ^ t1
        t2 = ~r3
        t3 = r1 ^ t1
        t4 = t3 | (r3 ^ t2)
        r1 = r0 ^ t4
        r0 = (r2 ^ t3) ^ (r3 | r1)
        r2 = (t0 ^ r1) ^ (r0 ^ (r0 & r3))

    # Версии S-блоков для работы с массивом
    def _apply_sb0(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb0(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3

    def _apply_sb1(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb1(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3

    def _apply_sb2(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb2(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3

    def _apply_sb3(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb3(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3

    def _apply_sb4(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb4(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3

    def _apply_sb5(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb5(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3

    def _apply_sb6(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb6(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3

    def _apply_sb7(self, subkeys, i0, i1, i2, i3):
        r0, r1, r2, r3 = subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3]
        self._sb7(r0, r1, r2, r3)
        subkeys[i0], subkeys[i1], subkeys[i2], subkeys[i3] = r0, r1, r2, r3