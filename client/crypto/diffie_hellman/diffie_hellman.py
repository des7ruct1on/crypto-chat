from typing import Tuple, Set
import random
import secrets
import time
from colorama import Fore, Style, init
from pyfiglet import Figlet
import sys


class DiffieHellman:

    @staticmethod
    def _print_banner():
        """Красивый баннер для отображения при вызове методов"""
        init()
        f = Figlet(font='slant')
        print(Fore.CYAN + f.renderText('Diffie-Hellman') + Style.RESET_ALL)
        print(Fore.YELLOW + "🔒 Secure Key Exchange Protocol" + Style.RESET_ALL)
        print("-" * 50)

    @staticmethod
    def _animate_loading(message: str, duration: int = 2):
        """Анимация загрузки"""
        print(Fore.GREEN + message + Style.RESET_ALL, end='')
        for _ in range(5):
            time.sleep(duration / 5)
            print(".", end='')
            sys.stdout.flush()
        print()

    @staticmethod
    def _print_success(message: str):
        """Стилизованный вывод успешного результата"""
        print(Fore.GREEN + "✓ " + message + Style.RESET_ALL)

    @staticmethod
    def _print_param(name: str, value: int, color=Fore.BLUE):
        """Красивый вывод параметров"""
        print(f"{color}{name}: {Fore.WHITE}{value}{Style.RESET_ALL}")

    @staticmethod
    def is_prime(n: int, rounds: int = 128) -> bool:
        DiffieHellman._animate_loading("Checking primality")
        if n <= 1:
            DiffieHellman._print_success(f"{n} is not prime")
            return False
        if n <= 3:
            DiffieHellman._print_success(f"{n} is prime")
            return True
        if n % 2 == 0:
            DiffieHellman._print_success(f"{n} is not prime (even)")
            return False

        small_primes = [3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
        for p in small_primes:
            if n % p == 0:
                result = n == p
                if result:
                    DiffieHellman._print_success(f"{n} is prime")
                else:
                    DiffieHellman._print_success(f"{n} is not prime (divisible by {p})")
                return result

        d = n - 1
        s = 0
        while d % 2 == 0:
            d //= 2
            s += 1

        for _ in range(rounds):
            a = random.randint(2, n - 2)
            x = pow(a, d, n)
            if x == 1 or x == n - 1:
                continue
            for _ in range(s - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                DiffieHellman._print_success(f"{n} is not prime (failed Miller-Rabin test)")
                return False

        DiffieHellman._print_success(f"{n} is probably prime (passed {rounds} Miller-Rabin tests)")
        return True

    @staticmethod
    def generate_large_prime(bits: int = 2048) -> int:
        DiffieHellman._print_banner()
        if bits < 8:
            raise ValueError("Bit length must be at least 8.")

        DiffieHellman._animate_loading(f"Generating {bits}-bit prime")
        while True:
            num = secrets.randbits(bits)
            num |= (1 << bits - 1) | 1
            if DiffieHellman.is_prime(num):
                DiffieHellman._print_param("Generated prime", num)
                return num

    @staticmethod
    def prime_factors(n: int) -> Set[int]:
        DiffieHellman._animate_loading("Calculating prime factors")
        factors = set()
        while n % 2 == 0:
            factors.add(2)
            n //= 2
        i = 3
        max_factor = int(n ** 0.5) + 1
        while i <= max_factor:
            while n % i == 0:
                factors.add(i)
                n //= i
                max_factor = int(n ** 0.5) + 1
            i += 2
        if n > 1:
            factors.add(n)

        DiffieHellman._print_param("Prime factors", ", ".join(map(str, factors))) if factors else None
        return factors

    @staticmethod
    def find_primitive_root(p: int) -> int:
        DiffieHellman._animate_loading(f"Finding primitive root for {p}")
        if not DiffieHellman.is_prime(p):
            raise ValueError("Modulus p must be a prime number.")
        if p == 2:
            return 1
        phi = p - 1
        factors = DiffieHellman.prime_factors(phi)
        for g in range(2, p):
            if all(pow(g, phi // factor, p) != 1 for factor in factors):
                DiffieHellman._print_param("Primitive root found", g, Fore.MAGENTA)
                return g
        raise ValueError(f"No primitive root found for prime p = {p}.")

    @staticmethod
    def generate_dh_parameters(bits: int = 64) -> Tuple[int, int]:
        DiffieHellman._print_banner()
        DiffieHellman._animate_loading("Generating DH parameters")
        p = DiffieHellman.generate_large_prime(bits)
        g = DiffieHellman.find_primitive_root(p)
        DiffieHellman._print_param("Prime modulus (p)", p)
        DiffieHellman._print_param("Generator (g)", g, Fore.MAGENTA)
        return p, g

    @staticmethod
    def generate_private_key(p: int) -> int:
        DiffieHellman._animate_loading("Generating private key")
        key = secrets.randbelow(p - 3) + 2
        DiffieHellman._print_param("Private key", key, Fore.RED)
        return key

    @staticmethod
    def generate_public_key(p: int, g: int, private_key: int) -> int:
        DiffieHellman._animate_loading("Calculating public key")
        key = pow(g, private_key, p)
        DiffieHellman._print_param("Public key", key, Fore.YELLOW)
        return key

    @staticmethod
    def generate_shared_secret(p: int, peer_public_key: int, private_key: int) -> int:
        DiffieHellman._animate_loading("Computing shared secret")
        secret = pow(peer_public_key, private_key, p)
        DiffieHellman._print_param("Shared secret", secret, Fore.GREEN)
        print(Fore.CYAN + "=" * 50 + Style.RESET_ALL)
        return secret