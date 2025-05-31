from datetime import datetime
from passlib.context import CryptContext
from fastapi import HTTPException, status
from uuid import uuid4

from repositories.chat_repository import ChatRepository
from db.models.chat import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, chat_repository: ChatRepository):
        self.chat_repository = chat_repository

    async def register(self, username: str, password: str) -> User:
        existing_user = await self.chat_repository.get_user_by_username(username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken"
            )

        password_hash = self._hash_password(password)
        user = User(
            id=str(uuid4()),
            username=username,
            password_hash=password_hash,
            created_at=datetime.utcnow()
        )

        await self.chat_repository.create_user(user)
        return user

    async def authenticate(self, username: str, password: str) -> User:
        user = await self.chat_repository.get_user_by_username(username)
        if not user or not self._verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )

        return user.id

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
