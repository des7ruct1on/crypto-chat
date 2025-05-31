from pydantic import BaseModel
from typing import Literal, Optional

class KafkaMessagePayload(BaseModel):
    message_id: str
    chat_id: str
    sender: str
    encrypted_message: str
    iv_nonce: str
    is_file: bool
    file_name: Optional[str] = None
    timestamp: str

class KafkaChatMessageEvent(BaseModel):
    type: Literal['new_message'] = 'new_message'
    chat_id: str
    sender: str
    message: KafkaMessagePayload
