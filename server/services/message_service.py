from fastapi import HTTPException, status
from uuid import uuid4

from db.models.chat import ChatStatus
from repositories.chat_repository import ChatRepository
from infrastructure.messaging.kafka.producer import KafkaEventProducer
from api.v1.schemas.message import SendMessageRequest, SendMessageResponse

class MessageService:

    def __init__(self, repo: ChatRepository, producer: KafkaEventProducer):
        self.repo = repo
        self.producer = producer
    
    async def send_message(self, data: SendMessageRequest) -> SendMessageResponse:
        chat = await self.repo.get_chat(data.chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found")
        
        participants = await self.repo.get_participants(data.chat_id)
        if data.user_id not in [p.user_id for p in participants]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a participant")

        chat_status = await self.repo.get_chat_status(data.chat_id)
        if not chat_status == ChatStatus.secure:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encryption not established for this chat")

        message_id = str(uuid4())
        recipient = [p.user_id for p in participants if p.user_id != data.user_id][0]
        
        message = {
            "message_id": message_id,
            "chat_id": data.chat_id,
            "sender": data.user_id,
            "recipient": recipient,
            "encrypted_message": data.encrypted_message,
            "iv_nonce": data.iv_nonce,
            "is_file": data.is_file,
            "file_name": data.file_name,
            "timestamp": data.timestamp.isoformat()
        }
        
        await self.producer.send_event("chat_messages", {
            "type": "file" if data.is_file else "message",
            "chat_id": data.chat_id,
            "sender": data.user_id,
            "recipient": recipient,
            "data": message
        })

        return SendMessageResponse(
            chat_id=data.chat_id,
            user_id=data.user_id,
            message_id=message_id
        )
