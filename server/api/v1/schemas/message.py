from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class BaseMessageActionMeta(BaseModel):
    chat_id: str
    user_id: str

class SendMessageRequest(BaseMessageActionMeta):
    encrypted_message: str
    iv_nonce: str
    is_file: bool
    file_name: Optional[str]
    timestamp: datetime

class SendMessageResponse(BaseMessageActionMeta):
    status: Literal['sent'] = Field(default='sent')
    message_id: str
