from abc import ABC, abstractmethod
from typing import Optional, Callable, List, Tuple
import os
from crypto.base.modes import PaddingMode, CipherMode
from crypto.base.cipher import SymmetricCipher

class MacGuffinCipher(SymmetricCipher):
    BLOCK_SIZE = 8  # 64 бита
    ALLOWED_KEY_SIZES = [16]  # 128 битный ключ

    def __init__(self, key: bytes):
        super().__init__(key)
        self._round_keys = self._expand_key(key)

    def _expand_key(self, key: bytes) -> List[List[int]]:
        """Преобразуем ключ в формат для алгоритма Маггафина"""
        if len(key) != 16:
            raise ValueError("Key must be 16 bytes (128 bits) long")

        # Преобразуем ключ в 128-битное число
        unic_key = int.from_bytes(key, byteorder='big')
        return self.make_key(unic_key)

    @staticmethod
    def split_data(data: int) -> Tuple[int, int, int, int]:
        """Разбиваем 64 бита на 4 части по 16 бит"""
        num0 = (data >> 48) & 0xFFFF
        num1 = (data >> 32) & 0xFFFF
        num2 = (data >> 16) & 0xFFFF
        num3 = data & 0xFFFF
        return num0, num1, num2, num3

    @staticmethod
    def permutation(num1: int, num2: int, num3: int) -> int:
        """Функция перестановки"""
        sbox = MacGuffinCipher.get_perm_ind(num1, num2, num3)
        tempArray2bit = MacGuffinCipher.change_6_to_2_bit(sbox)
        return MacGuffinCipher.union(tempArray2bit)

    @staticmethod
    def get_perm_ind(num1: int, num2: int, num3: int) -> List[int]:
        """Генерация индексов для S-блоков"""
        n1 = format(num1, '016b')[::-1]
        n2 = format(num2, '016b')[::-1]
        n3 = format(num3, '016b')[::-1]

        sbox = [
            int(n3[13] + n3[11] + n2[9] + n2[6] + n1[5] + n1[2], 2),
            int(n3[14] + n3[8] + n2[10] + n2[7] + n1[4] + n1[1], 2),
            int(n3[15] + n3[0] + n2[13] + n2[8] + n1[6] + n1[3], 2),
            int(n3[10] + n3[4] + n2[2] + n2[1] + n1[14] + n1[12], 2),
            int(n3[12] + n3[6] + n2[14] + n2[3] + n1[10] + n1[0], 2),
            int(n3[5] + n3[1] + n2[15] + n2[12] + n1[8] + n1[7], 2),
            int(n3[7] + n3[2] + n2[11] + n2[5] + n1[15] + n1[9], 2),
            int(n3[9] + n3[3] + n2[4] + n2[0] + n1[13] + n1[11], 2)
        ]
        return sbox

    @staticmethod
    def change_6_to_2_bit(array: List[int]) -> List[int]:
        """Применение S-блоков"""
        table = [
        # S1
        [2, 0, 0, 3, 3, 1, 1, 0, 0, 2, 3, 0, 3, 3, 2, 1,
         1, 2, 2, 0, 0, 2, 2, 3, 1, 3, 3, 1, 0, 1, 1, 2,
         0, 3, 1, 2, 2, 2, 2, 0, 3, 0, 0, 3, 0, 1, 3, 1,
         3, 1, 2, 3, 3, 1, 1, 2, 1, 2, 2, 0, 1, 0, 0, 3],

        # S2
        [3, 1, 1, 3, 2, 0, 2, 1, 0, 3, 3, 0, 1, 2, 0, 2,
         3, 2, 1, 0, 0, 1, 3, 2, 2, 0, 0, 3, 1, 3, 2, 1,
         0, 3, 2, 2, 1, 2, 3, 1, 2, 1, 0, 3, 3, 0, 1, 0,
         1, 3, 2, 0, 2, 1, 0, 2, 3, 0, 1, 1, 0, 2, 3, 3],

        # S3
        [2, 3, 1, 0, 2, 3, 0, 1, 3, 0, 1, 3, 2, 1, 0, 3,
         1, 0, 0, 1, 2, 0, 1, 2, 3, 1, 2, 2, 0, 2, 3, 3,
         2, 1, 3, 1, 0, 3, 3, 0, 2, 0, 3, 3, 1, 2, 0, 1,
         3, 0, 1, 3, 0, 2, 2, 1, 1, 3, 2, 1, 2, 0, 1, 2],

        # S4
        [1, 3, 3, 2, 2, 3, 1, 1, 0, 0, 0, 3, 3, 0, 2, 1,
         1, 0, 0, 1, 2, 0, 1, 2, 3, 1, 2, 2, 0, 2, 3, 3,
         2, 1, 0, 3, 3, 0, 0, 0, 2, 2, 3, 1, 1, 3, 3, 2,
         3, 3, 1, 0, 1, 1, 2, 3, 1, 2, 0, 1, 2, 0, 0, 2],

        # S5
        [0, 2, 3, 2, 2, 1, 0, 2, 3, 1, 1, 0, 3, 3, 2, 3,
         0, 3, 0, 2, 1, 2, 3, 1, 2, 1, 3, 2, 1, 0, 2, 1,
         3, 1, 0, 3, 3, 3, 3, 2, 2, 1, 1, 0, 1, 2, 2, 1,
         2, 3, 3, 1, 0, 0, 2, 3, 0, 2, 1, 0, 3, 1, 0, 2],

        # S6
        [2, 2, 1, 3, 2, 0, 3, 0, 3, 1, 0, 2, 0, 3, 2, 1,
         0, 0, 3, 1, 1, 3, 0, 2, 2, 0, 1, 3, 1, 1, 3, 2,
         3, 0, 2, 1, 3, 0, 1, 2, 0, 3, 2, 1, 2, 3, 1, 2,
         1, 3, 0, 2, 0, 1, 2, 1, 1, 0, 3, 0, 3, 2, 0, 3],

        # S7
        [0, 3, 3, 0, 0, 3, 2, 1, 3, 0, 0, 3, 2, 1, 3, 2,
         1, 2, 2, 1, 3, 1, 1, 2, 1, 0, 2, 3, 0, 2, 1, 0,
         1, 0, 0, 3, 3, 3, 3, 2, 2, 1, 1, 0, 1, 2, 2, 1,
         2, 3, 3, 1, 0, 0, 2, 3, 0, 2, 1, 0, 3, 1, 0, 2],

        # S8
        [3, 1, 0, 3, 2, 1, 1, 0, 0, 1, 2, 0, 3, 2, 1, 3,
         1, 0, 0, 1, 3, 2, 2, 3, 0, 1, 2, 3, 3, 0, 2, 1,
         0, 3, 1, 0, 1, 0, 3, 2, 1, 3, 0, 2, 0, 1, 2, 3,
         3, 1, 0, 2, 2, 0, 3, 1, 0, 2, 2, 3, 1, 0, 3, 2]
    ]
        return [table[i][n] for i, n in enumerate(array)]

    @staticmethod
    def union(array: List[int]) -> int:
        """Объединение результатов S-блоков"""
        bits = ''.join(f"{x:02b}"[::-1] for x in array)
        return int(bits, 2)

    def lap(self, data: int, key: List[int]) -> int:
        """Один раунд шифрования"""
        num0, num1, num2, num3 = self.split_data(data)
        tmp1 = num1 ^ key[0]
        tmp2 = num2 ^ key[1]
        tmp3 = num3 ^ key[2]
        tmp = self.permutation(tmp1, tmp2, tmp3)
        num0 ^= tmp
        return (num1 << 48) | (num2 << 32) | (num3 << 16) | num0

    def back_lap(self, data: int, key: List[int]) -> int:
        """Один раунд расшифровки"""
        num0, num1, num2, num3 = self.split_data(data)
        tmp1 = num1 ^ key[0]
        tmp2 = num2 ^ key[1]
        tmp3 = num3 ^ key[2]
        tmp = self.permutation(tmp1, tmp2, tmp3)
        num0 ^= tmp
        return (num3 << 48) | (num0 << 32) | (num1 << 16) | num2

    def encrypt_block(self, plaintext: bytes) -> bytes:
        """Шифрование одного блока"""
        if len(plaintext) != self.BLOCK_SIZE:
            raise ValueError(f"Block size must be {self.BLOCK_SIZE} bytes")

        data = int.from_bytes(plaintext, byteorder='big')
        for i in range(32):
            data = self.lap(data, self._round_keys[i])
        return data.to_bytes(self.BLOCK_SIZE, byteorder='big')

    def decrypt_block(self, ciphertext: bytes) -> bytes:
        """Расшифровка одного блока"""
        if len(ciphertext) != self.BLOCK_SIZE:
            raise ValueError(f"Block size must be {self.BLOCK_SIZE} bytes")

        data = int.from_bytes(ciphertext, byteorder='big')
        temp_data = self.recombination(data)

        for i in range(31, -1, -1):
            temp_data = self.back_lap(temp_data, self._round_keys[i])

        temp_data = self.recombination(temp_data)
        temp_data = self.recombination(temp_data)
        temp_data = self.recombination(temp_data)

        return temp_data.to_bytes(self.BLOCK_SIZE, byteorder='big')

    @staticmethod
    def recombination(data: int) -> int:
        """Перестановка блоков"""
        num0, num1, num2, num3 = MacGuffinCipher.split_data(data)
        return (num3 << 48) | (num0 << 32) | (num1 << 16) | num2

    @staticmethod
    def make_key(unic_key: int) -> List[List[int]]:
        """Генерация раундовых ключей"""
        key = [[0] * 3 for _ in range(32)]
        part1 = unic_key >> 64
        part2 = unic_key & ((1 << 64) - 1)

        for i in range(32):
            part1 = MacGuffinCipher.encrypt_static(part1, key)
            left = part1 >> 48
            tmp = part1 & ((1 << 48) - 1)
            a = tmp >> 32
            tmp &= ((1 << 32) - 1)
            b = tmp >> 16
            key[i] = [left, a, b]

        for i in range(32):
            part2 = MacGuffinCipher.encrypt_static(part2, key)
            left = part2 >> 48
            tmp = part2 & ((1 << 48) - 1)
            a = tmp >> 32
            tmp &= ((1 << 32) - 1)
            b = tmp >> 16
            key[i][0] ^= left
            key[i][1] ^= a
            key[i][2] ^= b

        return key

    @staticmethod
    def encrypt_static(data: int, key: List[List[int]]) -> int:
        """Статический метод шифрования для генерации ключей"""
        for i in range(32):
            num0, num1, num2, num3 = MacGuffinCipher.split_data(data)
            tmp1 = num1 ^ key[i][0]
            tmp2 = num2 ^ key[i][1]
            tmp3 = num3 ^ key[i][2]
            tmp = MacGuffinCipher.permutation(tmp1, tmp2, tmp3)
            num0 ^= tmp
            data = (num1 << 48) | (num2 << 32) | (num3 << 16) | num0
        return data