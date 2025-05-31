from pydantic import BaseModel, Field
from enum import Enum
from typing import Literal

class Algorithm(str, Enum):
    macguffin = "MACGUFFIN"
    serpent = "SERPENT"

class EncryptionMode(str, Enum):
    ECB = "ECB"
    CBC = "CBC"
    PCBC = "PCBC"
    CFB = "CFB"
    OFB = "OFB"
    CTR = "CTR"
    RANDOM_DELTA = "RANDOM_DELTA"

class PaddingMode(str, Enum):
    ZEROS = "ZEROS"
    ANSI_X923 = "ANSI_X923"
    PKCS7 = "PKCS7"
    ISO_10126 = "ISO_10126"

class BaseChatActionMeta(BaseModel):
    chat_id: str
    user_id: str

class CreateChatRequest(BaseModel):
    user_id: str
    algorithm: Algorithm
    encryption_mode: EncryptionMode
    padding_mode: PaddingMode

class JoinChatRequest(BaseChatActionMeta):
    pass

class LeaveChatRequest(BaseChatActionMeta):
    pass

class CloseChatRequest(BaseChatActionMeta):
    pass

class CreateChatResponse(BaseChatActionMeta):
    status: Literal['created'] = Field(default='created')

class JoinChatResponse(BaseChatActionMeta):
    status: Literal['joined'] = Field(default='joined')
    algorithm: Algorithm
    encryption_mode: EncryptionMode
    padding_mode: PaddingMode

class LeaveChatResponse(BaseChatActionMeta):
    status: Literal['leaved'] = Field(default='leaved')

class CloseChatResponse(BaseChatActionMeta):
    status: Literal['closed'] = Field(default='closed')

class GetChatEncryptionStatusResponse(BaseChatActionMeta):
    status: Literal['success'] = Field(default='success')
    encryption_ready: bool
