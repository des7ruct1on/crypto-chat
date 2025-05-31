from pydantic import BaseModel, Field
from typing import Optional, Literal

class BaseKeyActionMeta(BaseModel):
    chat_id: str

class GetDHParamsResponse(BaseKeyActionMeta):
    p: int
    g: int

class StorePublicKeyRequest(BaseKeyActionMeta):
    user_id: str
    public_key: int

class StorePublicKeyResponse(BaseKeyActionMeta):
    status: Literal['stored'] = Field(default='stored')
    user_id: str
    encryption_ready: bool
    other_participant: Optional[str]
    other_public_key: Optional[int]

class GetParticipantKeyResponse(BaseKeyActionMeta):
    participant_id: Optional[str]
    public_key: Optional[int]
