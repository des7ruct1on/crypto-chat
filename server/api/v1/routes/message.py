from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from di.container import Container
from services.message_service import MessageService
from api.v1.schemas.message import SendMessageRequest, SendMessageResponse

router = APIRouter(prefix="/message", tags=["Message"])

@router.post("/send", response_model=SendMessageResponse)
@inject
async def send_message(
    request: SendMessageRequest,
    message_service: MessageService = Depends(Provide[Container.services.provided.message]),
):  
    return await message_service.send_message(request)
