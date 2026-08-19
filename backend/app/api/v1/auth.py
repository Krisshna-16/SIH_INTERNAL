import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.auth.security import verify_password, get_password_hash, create_access_token
from app.auth.dependencies import get_current_user

router = APIRouter(tags=["auth"])

ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "true").lower() == "true"


class LoginRequest(BaseModel):
    username: str = Field(..., example="investigator")
    password: str = Field(..., example="demo123")


class RegisterRequest(BaseModel):
    username: str = Field(..., example="investigator2")
    password: str = Field(..., example="securepass123")


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates investigator credentials and returns JWT bearer token.
    Generic 401 error message for security.
    """
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role.value})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role.value,
            "created_at": user.created_at.isoformat(),
        },
    }


@router.post("/auth/register", response_model=UserResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Demo user registration endpoint. Gated by ALLOW_REGISTRATION environment setting.
    """
    if not ALLOW_REGISTRATION:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User registration is disabled in production environment."
        )

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered."
        )

    hashed_pw = get_password_hash(payload.password)
    user = User(username=payload.username, hashed_password=hashed_pw, role=UserRole.INVESTIGATOR)
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "role": user.role.value,
        "created_at": user.created_at.isoformat(),
    }


@router.get("/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns currently authenticated investigator profile."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role.value,
        "created_at": current_user.created_at.isoformat(),
    }
