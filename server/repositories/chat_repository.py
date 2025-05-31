from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from db.models.chat import Chat, Participant, ChatStatus, User

class ChatRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_chat(self, chat_id: str) -> Chat | None:
        return await self._session.get(Chat, chat_id)

    async def create_chat(self, chat: Chat):
        self._session.add(chat)
        await self._session.commit()

    async def add_participant(self, participant: Participant):
        self._session.add(participant)
        await self._session.commit()

    async def add_chat_with_creator(self, chat: Chat, creator: Participant):
        self._session.add_all([chat, creator])
        await self._session.commit()
    
    async def get_chat_status(self, chat_id: str) -> ChatStatus:
        chat = await self.get_chat(chat_id)
        if chat is None:
            return None
        return chat.status

    async def set_chat_status(self, chat_id: str, status: ChatStatus):
        chat = await self.get_chat(chat_id)
        if chat is None:
            return
        chat.status = status
        await self._session.commit()

    async def update_participant_public_key(self, chat_id: str, user_id: str, public_key: str):
        participant = await self.get_participant(chat_id, user_id)
        if participant is None:
            return
        participant.public_key = public_key
        await self._session.commit()

    async def get_participant(self, chat_id: str, user_id: str) -> Participant | None:
        result = await self._session.execute(
            select(Participant).where(
                Participant.chat_id == chat_id,
                Participant.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_participants(self, chat_id: str) -> list[Participant]:
        result = await self._session.execute(
            select(Participant).where(Participant.chat_id == chat_id)
        )
        return result.scalars().all()

    async def delete_participant(self, chat_id: str, user_id: str):
        await self._session.execute(
            delete(Participant).where(
                Participant.chat_id == chat_id,
                Participant.user_id == user_id
            )
        )
        await self._session.commit()

    async def delete_chat(self, chat_id: str):
        chat = await self.get_chat(chat_id)
        if chat is None:
            return
        await self._session.delete(chat)
        await self._session.commit()

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

    async def create_user(self, user: User):
        self._session.add(user)
        await self._session.commit()
        await self._session.refresh(user)
