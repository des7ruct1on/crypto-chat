from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Settings
from di.datatypes import Services, KafkaComponents, Repositories
from infrastructure.messaging.kafka.producer import KafkaEventProducer
from repositories.chat_repository import ChatRepository
from services.chat_service import ChatService
from services.message_service import MessageService
from services.key_service import KeyService
from services.auth_service import AuthService

def init_repositories(session: AsyncSession) -> Repositories:
    chat = ChatRepository(session)

    return Repositories(
        chat=chat
    )

def init_kafka_components(settings: Settings) -> KafkaComponents:
    producer = KafkaEventProducer(settings.kafka_bootstrap_servers)

    return KafkaComponents(
        producer=producer
    )

def init_services(chat_repository: ChatRepository, producer: KafkaEventProducer) -> Services:
    chat = ChatService(chat_repository, producer)

    message = MessageService(chat_repository, producer)

    key = KeyService(chat_repository, producer)

    auth = AuthService(chat_repository)

    return Services(
        chat=chat,
        message=message,
        key=key,
        auth=auth
    )
