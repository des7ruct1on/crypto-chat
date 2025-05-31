import asyncio
import json
from aiokafka import AIOKafkaConsumer

class KafkaEventConsumer:
    def __init__(self, bootstrap_servers: str, topics: list, group_id: str):
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id=self.group_id,
            enable_auto_commit=True
        )
        await self._consumer.start()

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._consumer is None:
            raise StopAsyncIteration

        try:
            msg = await self._consumer.getone()
            return msg
        except asyncio.CancelledError:
            raise StopAsyncIteration
        except Exception as e:
            raise StopAsyncIteration
