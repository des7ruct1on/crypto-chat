from fastapi import APIRouter, Depends, status
from api.v1.schemas.auth import RegisterRequest, LoginRequest
from services.auth_service import AuthService
from fastapi import APIRouter, Depends
from dependency_injector.wiring import inject, Provide

from di.container import Container

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
@inject
async def register(
    payload: RegisterRequest,
    auth_service: AuthService = Depends(Provide[Container.services.provided.auth])
):
    user = await auth_service.register(username=payload.username, password=payload.password)
    return {
        "id": user.id,
        "username": user.username,
        "created_at": user.created_at
    }

@router.post("/login")
@inject
async def login(
    payload: LoginRequest,
    auth_service: AuthService = Depends(Provide[Container.services.provided.auth])
):
    id = await auth_service.authenticate(username=payload.username, password=payload.password)
    return {
        "id": id
    }
