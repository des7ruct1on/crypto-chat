from repositories.chat_repository import ChatRepository
from infrastructure.messaging.kafka.producer import KafkaEventProducer
from db.models.chat import ChatStatus
from api.v1.schemas.key import GetDHParamsResponse, StorePublicKeyRequest, StorePublicKeyResponse, GetParticipantKeyResponse

class KeyService:

    def __init__(self, repo: ChatRepository, producer: KafkaEventProducer):
        self.repo = repo
        self.producer = producer

    async def get_chat_dh_params(self, chat_id: str) -> GetDHParamsResponse:
        chat = await self.repo.get_chat(chat_id)
        return GetDHParamsResponse(
            chat_id=chat_id,
            p=chat.p,
            g=chat.g
        )
    
    async def store_public_key(self, data: StorePublicKeyRequest) -> StorePublicKeyResponse:        
        await self.repo.update_participant_public_key(data.chat_id, data.user_id, data.public_key)

        participants = await self.repo.get_participants(data.chat_id)
        
        all_keys_exchanged = all(p.public_key for p in participants)
        if all_keys_exchanged:
            await self.repo.set_chat_status(data.chat_id, ChatStatus.secure)

        other_participant_id = None
        participants = await self.repo.get_participants(data.chat_id)
        for p in participants:
            if p.user_id != data.user_id:
                other_participant_id = p.user_id

        other_participant = await self.repo.get_participant(data.chat_id, other_participant_id)
        other_public_key = other_participant.public_key if other_participant else None
        
        if all_keys_exchanged:
            await self.producer.send_event("chat_messages", {
                "type": "encryption_ready",
                "chat_id": data.chat_id
            })
        
        return StorePublicKeyResponse(
            chat_id=data.chat_id,
            user_id=data.user_id,
            encryption_ready=all_keys_exchanged,
            other_participant=other_participant.user_id if other_participant else None,
            other_public_key=other_public_key
        )  

    async def get_participant_key(self, chat_id: str, user_id: str) -> GetParticipantKeyResponse:
        other_participant_id = None
        participants = await self.repo.get_participants(chat_id)
        for p in participants:
            if p.user_id != user_id:
                other_participant_id = p.user_id

        other_participant = await self.repo.get_participant(chat_id, other_participant_id)
        other_public_key = other_participant.public_key if other_participant else None
        
        return GetParticipantKeyResponse(
            chat_id=chat_id,
            participant_id=other_participant.user_id if other_participant else None,
            public_key=other_public_key
        )
