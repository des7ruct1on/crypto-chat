from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from di.container import Container
from services.key_service import KeyService
from api.v1.schemas.key import GetDHParamsResponse, StorePublicKeyRequest, StorePublicKeyResponse, GetParticipantKeyResponse

router = APIRouter(prefix="/key", tags=["Key"])

@router.get("/{chat_id}/dh_params", response_model=GetDHParamsResponse)
@inject
async def get_dh_params(
    chat_id: str,
    key_service: KeyService = Depends(Provide[Container.services.provided.key])
):
    return await key_service.get_chat_dh_params(chat_id)


@router.post("/public_key", response_model=StorePublicKeyResponse)
@inject
async def store_public_key(
    request: StorePublicKeyRequest,
    key_service: KeyService = Depends(Provide[Container.services.provided.key])
):
    return await key_service.store_public_key(request)


@router.get("/{chat_id}/participant_key", response_model=GetParticipantKeyResponse)
@inject
async def get_participant_key(
    chat_id: str, 
    user_id: str,
    key_service: KeyService = Depends(Provide[Container.services.provided.key])
):
    return await key_service.get_participant_key(chat_id, user_id)
