from dataclasses import dataclass

from services.chat_service import ChatService
from services.message_service import MessageService
from services.key_service import KeyService
from services.auth_service import AuthService
from repositories.chat_repository import ChatRepository
from infrastructure.messaging.kafka.producer import KafkaEventProducer

@dataclass
class Repositories:
    chat: ChatRepository

@dataclass
class KafkaComponents:
    producer: KafkaEventProducer

@dataclass
class Services:
    chat: ChatService
    message: MessageService
    key: KeyService
    auth: AuthService
