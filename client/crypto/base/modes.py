from enum import Enum

class PaddingMode(Enum):
    ZEROS = 0
    ANSI_X923 = 1
    PKCS7 = 2
    ISO_10126 = 3

class CipherMode(Enum):
    ECB = 0
    CBC = 1
    PCBC = 2
    CFB = 3
    OFB = 4
    CTR = 5
    RANDOM_DELTA = 6
