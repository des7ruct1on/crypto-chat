from typing import Tuple
import random

class DiffieHellman:
    
    @staticmethod
    def is_prime(n: int, k: int = 128) -> bool:
        if n <= 1:
            return False
        elif n <= 3:
            return True
        elif n % 2 == 0:
            return False
        
        small_primes = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
        for p in small_primes:
            if n % p == 0:
                return n == p
        
        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1
        
        for _ in range(k):
            a = random.randint(2, n - 2)
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for __ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        return True

    @staticmethod
    def generate_large_prime(bits: int = 2048) -> int:
        if bits < 8:
            raise ValueError("Количество бит должно быть не менее 8")
            
        while True:
            num = random.getrandbits(bits)
            
            num |= (1 << bits - 1) | 1
            
            if DiffieHellman.is_prime(num):
                return num

    @staticmethod
    def prime_factors(n: int) -> set:
        factors = set()
        
        while n % 2 == 0:
            factors.add(2)
            n = n // 2

        i = 3
        max_factor = int(n**0.5) + 1
        while i <= max_factor:
            while n % i == 0:
                factors.add(i)
                n = n // i
                max_factor = int(n**0.5) + 1
            i += 2
        
        if n > 1:
            factors.add(n)
        return factors

    @staticmethod
    def find_primitive_root(p: int) -> int:
        if not DiffieHellman.is_prime(p):
            raise ValueError("Модуль p должен быть простым числом")
        
        if p == 2:
            return 1
        
        phi = p - 1
        factors = DiffieHellman.prime_factors(phi)
        
        for g in range(2, p):
            if all(pow(g, phi // factor, p) != 1 for factor in factors):
                return g
        raise ValueError(f"Первообразный корень по модулю {p} не найден")

    @staticmethod
    def generate_dh_parameters(bits: int = 64) -> Tuple[int, int]:
        p = DiffieHellman.generate_large_prime(bits)
        g = DiffieHellman.find_primitive_root(p)
        return p, g

    @staticmethod
    def generate_private_key(p: int) -> int:
        return random.randint(2, p - 2)

    @staticmethod
    def generate_public_key(p: int, g: int, private_key: int) -> int:
        return pow(g, private_key, p)

    @staticmethod
    def generate_shared_secret(p: int, public_key: int, private_key: int) -> int:
        return pow(public_key, private_key, p)
