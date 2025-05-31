from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from di.container import Container
from services.chat_service import ChatService
from api.v1.schemas.chat import (
    JoinChatRequest, JoinChatResponse, 
    CloseChatRequest, CloseChatResponse, 
    LeaveChatRequest, LeaveChatResponse, 
    CreateChatRequest, CreateChatResponse,
    GetChatEncryptionStatusResponse
)

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/create", response_model=CreateChatResponse)
@inject
async def create_chat(
    request: CreateChatRequest,
    chat_service: ChatService = Depends(Provide[Container.services.provided.chat])
):
    return await chat_service.create_chat(request)

@router.post("/join", response_model=JoinChatResponse)
@inject
async def join_chat(
    request: JoinChatRequest,
    chat_service: ChatService = Depends(Provide[Container.services.provided.chat])
):
    return await chat_service.join_chat(request)

@router.post("/leave", response_model=LeaveChatResponse)
@inject
async def leave_chat(
    request: LeaveChatRequest,
    chat_service: ChatService = Depends(Provide[Container.services.provided.chat])
):
    return await chat_service.leave_chat(request)

@router.post("/close", response_model=CloseChatResponse)
@inject
async def close_chat(
    request: CloseChatRequest,
    chat_service: ChatService = Depends(Provide[Container.services.provided.chat])
):
    return await chat_service.close_chat(request)

@router.get("/{chat_id}/{user_id}/encryption_status", response_model=GetChatEncryptionStatusResponse)
@inject
async def close_chat(
    chat_id: str,
    user_id: str,
    chat_service: ChatService = Depends(Provide[Container.services.provided.chat])
):
    return await chat_service.get_chat_encryption_status(chat_id, user_id)
