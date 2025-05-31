from fastapi import FastAPI
from contextlib import asynccontextmanager

from di.container import Container

@asynccontextmanager
async def lifespan(app: FastAPI):
    container = Container()
    app.container = container

    container.init_resources()

    kafka = container.kafka_components()
    
    await kafka.producer.start()

    yield

    await kafka.producer.stop()

    container.shutdown_resources()
