from dependency_injector import containers, providers

from core.config import get_settings
from di.resources import (
    init_services,
    init_kafka_components,
    init_repositories,
)
from db.session import get_session

class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "api.v1.routes.chat",
            "api.v1.routes.key",
            "api.v1.routes.message",
            "api.v1.routes.auth"
        ]
    )

    config = providers.Singleton(get_settings)

    db_session = providers.Factory(get_session)

    repositories = providers.Singleton(
        init_repositories,
        session=db_session
    )

    kafka_components = providers.Resource(
        init_kafka_components,
        settings=config
    )

    services = providers.Singleton(
        init_services,
        chat_repository=repositories.provided.chat,
        producer=kafka_components.provided.producer,
    )
