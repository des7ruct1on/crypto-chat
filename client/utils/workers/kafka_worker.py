import asyncio
from PyQt5.QtCore import QObject, pyqtSignal

class KafkaWorker(QObject):
    message_received = pyqtSignal(dict)

    def __init__(self, kafka_consumer):
        super().__init__()
        self.consumer = kafka_consumer
        self._loop = asyncio.new_event_loop()
        self._task = None
        self._stopping = False

    def start(self):
        asyncio.set_event_loop(self._loop)
        self._task = self._loop.create_task(self.run_consumer())
        try:
            self._loop.run_until_complete(self._task)
        except asyncio.CancelledError:
            pass
        finally:
            pending = asyncio.all_tasks(self._loop)
            for task in pending:
                task.cancel()
            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            self._loop.close()

    async def run_consumer(self):
        await self.consumer.start()
        try:
            async for msg in self.consumer:
                if self._stopping:
                    break
                self.message_received.emit(msg.value)
        except asyncio.CancelledError:
            pass
        finally:
            await self.consumer.stop()

    def stop(self):
        self._stopping = True
        if self._task and not self._task.done():
            self._task.cancel()
