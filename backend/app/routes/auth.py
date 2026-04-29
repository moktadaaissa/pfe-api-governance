from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.auth_service import (
    authenticate_user,
    create_access_token,
    get_current_user
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest):
    user = authenticate_user(payload.username, payload.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "username": user["username"],
            "role": user["role"]
        }
    }


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user