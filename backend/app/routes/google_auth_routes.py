"""
Google OAuth Login Route
Verifies the Google ID token, creates or retrieves the user,
and returns a JWT with user status for the approval workflow.
"""

import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.models.user import User, UserStatus
from app.schemas.user_schema import GoogleLoginRequest, GoogleToken
from app.utils.auth import create_access_token, get_current_user
from app.services.supabase_auth import supabase_auth_verifier
from app.utils.role_detection import detect_role_from_email

google_auth_router = APIRouter(prefix="/auth", tags=["auth"])
supabase_bearer = OAuth2PasswordBearer(tokenUrl="auth/login")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


class ProfileUpdateRequest(BaseModel):
    registration_number: Optional[str] = None
    department: Optional[str] = None


@google_auth_router.patch("/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's optional profile details."""
    if payload.registration_number is not None:
        registration_number = payload.registration_number.strip()
        if not registration_number:
            raise HTTPException(status_code=422, detail="Registration number cannot be empty")
        current_user.registration_number = registration_number[:50]

    if payload.department is not None:
        current_user.department = payload.department.strip()[:100] or None

    await current_user.save()
    return {
        "message": "Profile updated",
        "registration_number": current_user.registration_number,
        "department": current_user.department,
    }


@google_auth_router.post("/google-login", response_model=GoogleToken)
async def google_login(body: GoogleLoginRequest):
    """
    Accepts a Google ID token from the frontend, verifies it,
    creates a new user (PENDING) or fetches the existing one,
    and returns an internal JWT along with the user's approval status.
    """
    # 1. Verify the Google ID token
    try:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "")
        idinfo = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            client_id,
            clock_skew_in_seconds=60
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {e}",
        )

    # 2. Extract profile info
    google_id = idinfo.get("sub")
    email = idinfo.get("email", "").lower()
    name = idinfo.get("name", email.split("@")[0])
    picture = idinfo.get("picture")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account has no email address.",
        )

    # 3. Find or create the user
    user = await User.find_one(User.email == email)

    if user is None:
        # New user — detect role and set as PENDING
        detected_role = detect_role_from_email(email)

        if detected_role == "external":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only @christuniversity.in or valid student domains are allowed.",
            )

        initial_status = (
            UserStatus.APPROVED if detected_role == "admin" else UserStatus.PENDING
        )

        user = User(
            name=name,
            email=email,
            google_id=google_id,
            picture=picture,
            role=detected_role,
            status=initial_status,
            hashed_password=None,  # No password for OAuth users
        )
        await user.assign_id()
        await user.insert()
    else:
        # Existing user — update Google fields if missing
        changed = False
        if not user.google_id:
            user.google_id = google_id
            changed = True
        if picture and user.picture != picture:
            user.picture = picture
            changed = True
        if changed:
            await user.save()

    # Update last_active timestamp on login
    user.last_active = datetime.utcnow()
    await user.save()

    # 4. Issue internal JWT (always issued, but frontend checks status)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "name": user.name}
    )

    return GoogleToken(
        access_token=access_token,
        token_type="bearer",
        status=user.status or "approved",
        user={
            "id": user.int_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status or "approved",
            "picture": user.picture,
        },
    )


@google_auth_router.post("/supabase-sync", response_model=GoogleToken)
async def supabase_sync(token: str = Depends(supabase_bearer)):
    """Provision the MongoDB profile for a user authenticated by Supabase Auth."""
    try:
        payload = supabase_auth_verifier.verify(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase session") from exc

    auth_user_id = payload.get("sub")
    email = (payload.get("email") or "").lower()
    if not auth_user_id or not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Supabase session has no user identity")

    user = await User.find_one(User.auth_user_id == auth_user_id) or await User.find_one(User.email == email)
    if user is None:
        detected_role = detect_role_from_email(email)
        if detected_role == "external":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only university accounts are allowed.")
        user = User(
            auth_user_id=auth_user_id,
            name=payload.get("user_metadata", {}).get("full_name") or email.split("@")[0],
            email=email,
            role=detected_role,
            status=UserStatus.APPROVED if detected_role == "admin" else UserStatus.PENDING,
            picture=payload.get("user_metadata", {}).get("avatar_url"),
        )
        await user.assign_id()
        await user.insert()
    elif not user.auth_user_id:
        user.auth_user_id = auth_user_id
        await user.save()

    user.last_active = datetime.utcnow()
    await user.save()
    return GoogleToken(
        access_token=token,
        token_type="bearer",
        status=user.status or "approved",
        user={"id": user.int_id, "name": user.name, "email": user.email, "role": user.role, "status": user.status, "picture": user.picture},
    )
