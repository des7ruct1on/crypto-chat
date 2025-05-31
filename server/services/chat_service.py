import logging
from uuid import uuid4
from datetime import datetime
from fastapi import HTTPException

from diffie_hellman.diffie_hellman import DiffieHellman
from infrastructure.messaging.kafka.producer import KafkaEventProducer
from repositories.chat_repository import ChatRepository
from db.models.chat import Chat, Participant, ChatStatus
from api.v1.schemas.chat import (
    JoinChatRequest, JoinChatResponse, 
    CloseChatRequest, CloseChatResponse, 
    LeaveChatRequest, LeaveChatResponse, 
    CreateChatRequest, CreateChatResponse,
    GetChatEncryptionStatusResponse
)

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, repo: ChatRepository, producer: KafkaEventProducer):
        self.repo = repo
        self.producer = producer

    async def create_chat(self, data: CreateChatRequest) -> CreateChatResponse:
        chat_id = str(uuid4())
        p, g = DiffieHellman.generate_dh_parameters()

        chat = Chat(
            id=chat_id,
            creator_id=data.user_id,
            algorithm=data.algorithm,
            encryption_mode=data.encryption_mode,
            padding_mode=data.padding_mode,
            p=p,
            g=g,
            status=ChatStatus.waiting,
            created_at=datetime.utcnow()
        )
        creator = Participant(chat_id=chat_id, user_id=data.user_id)

        await self.repo.add_chat_with_creator(chat, creator)

        logger.info(f"Chat {chat_id} created by user {data.user_id}")

        return CreateChatResponse(
            chat_id=chat_id,
            user_id=data.user_id
        )

    async def join_chat(self, data: JoinChatRequest) -> JoinChatResponse:
        chat = await self.repo.get_chat(data.chat_id)
        if not chat:
            logger.warning(f"Chat {data.chat_id} not found")
            raise HTTPException(status_code=400, detail="Cannot join chat")
        
        participants = await self.repo.get_participants(data.chat_id)

        if any(p.user_id == data.user_id for p in participants):
            logger.warning(f"User {data.user_id } already in chat {data.chat_id}")
            raise HTTPException(status_code=400, detail="Cannot join chat")

        if len(participants) >= 2:
            logger.warning(f"Chat {data.chat_id} is full")
            raise HTTPException(status_code=400, detail="Cannot join chat")

        await self.repo.add_participant(Participant(chat_id=data.chat_id, user_id=data.user_id ))
        if len(participants) + 1 == 2:
            await self.repo.set_chat_status(data.chat_id, ChatStatus.active)
        
        chat = await self.repo.get_chat(data.chat_id)

        await self.producer.send_event("chat_messages", {
            "type": "user_joined",
            "chat_id": data.chat_id,
            "user_id": data.user_id ,
            "status": chat.status
        })

        logger.info(f"User {data.user_id } joined chat {data.chat_id}")
        
        return JoinChatResponse(
            chat_id=data.chat_id,
            user_id=data.user_id,
            algorithm=chat.algorithm,
            encryption_mode=chat.encryption_mode,
            padding_mode=chat.padding_mode
        )

    async def leave_chat(self, data: LeaveChatRequest) -> LeaveChatResponse:
        chat = await self.repo.get_chat(data.chat_id)
        if not chat:
            raise HTTPException(status_code=400, detail="Cannot leave chat")

        await self.repo.delete_participant(data.chat_id, data.user_id)

        chat = await self.repo.get_chat(data.chat_id)

        is_creator =  chat is not None and chat.creator_id == data.user_id

        participants = await self.repo.get_participants(data.chat_id)
        if not participants or len(participants) == 0 or is_creator:
            await self.close_chat(CloseChatRequest(
                chat_id=data.chat_id,
                user_id=chat.creator_id
            ))
            logger.info(f"Chat {data.chat_id} deleted — no participants")
        else:
            await self.repo.set_chat_status(data.chat_id, ChatStatus.waiting)

        await self.producer.send_event("chat_messages", {
            "type": "user_left",
            "chat_id": data.chat_id,
            "user_id": data.user_id
        })

        logger.info(f"User {data.chat_id} left chat {data.chat_id}")
        return LeaveChatResponse(
            chat_id=data.chat_id,
            user_id=data.user_id
        )

    async def close_chat(self, data: CloseChatRequest) -> CloseChatResponse:
        chat = await self.repo.get_chat(data.chat_id)
        if not chat or chat.creator_id != data.user_id:
            logger.warning(f"User {data.user_id} is not the creator of chat {data.chat_id}")
            raise HTTPException(status_code=400, detail="Cannot close chat")

        await self.repo.delete_chat(chat.id)

        await self.producer.send_event("chat_messages", {
            "type": "chat_closed",
            "chat_id": data.chat_id,
            "closed_by": data.user_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        logger.info(f"Chat {data.chat_id} closed by creator {data.user_id}")
        return CloseChatResponse(
            chat_id=data.chat_id,
            user_id=data.user_id
        )

    async def get_chat_encryption_status(self, chat_id: str, user_id: str) -> GetChatEncryptionStatusResponse:
        chat = await self.repo.get_chat(chat_id)
    
        participants = await self.repo.get_participants(chat_id)

        if not chat or user_id not in [p.user_id for p in participants]:
            raise HTTPException(status_code=400, detail="Cannot get chat encryption status")

        chat_status = await self.repo.get_chat_status(chat_id)

        print(chat_status)

        is_ready = chat_status == ChatStatus.secure

        return GetChatEncryptionStatusResponse(
            chat_id=chat_id,
            user_id=user_id,
            encryption_ready=is_ready
        )
