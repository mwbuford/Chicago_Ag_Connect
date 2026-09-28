import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import Header, HTTPException

from backend.config import MARKETPLACE_DATA_DIR
from backend.models.marketplace import UserAccount, UserRole

USERS_FILE = MARKETPLACE_DATA_DIR / "users.json"
SESSIONS_FILE = MARKETPLACE_DATA_DIR / "sessions.json"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _load_json(path: Path, default):
    if not path.exists():
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


class AuthService:
    def __init__(self):
        self._users: Dict[str, Dict[str, Any]] = {}
        self._sessions: Dict[str, str] = {}
        self._load()

    def _load(self):
        raw_users = _load_json(USERS_FILE, {})
        self._users = raw_users
        self._sessions = _load_json(SESSIONS_FILE, {})

    def _persist(self):
        _save_json(USERS_FILE, self._users)
        _save_json(SESSIONS_FILE, self._sessions)

    def register(self, email: str, password: str, display_name: str, role: UserRole = UserRole.CONSUMER) -> tuple[str, UserAccount]:
        email_key = email.strip().lower()
        if email_key in self._users:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = str(uuid.uuid4())[:12]
        self._users[email_key] = {
            "id": user_id,
            "email": email_key,
            "display_name": display_name.strip(),
            "role": role.value,
            "password_hash": _hash_password(password),
            "vendor_id": None,
            "created_at": _utcnow().isoformat()
        }
        token = secrets.token_urlsafe(32)
        self._sessions[token] = user_id
        self._persist()
        return token, self._to_account(self._users[email_key])

    def login(self, email: str, password: str) -> tuple[str, UserAccount]:
        email_key = email.strip().lower()
        user = self._users.get(email_key)
        if not user or user["password_hash"] != _hash_password(password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = secrets.token_urlsafe(32)
        self._sessions[token] = user["id"]
        self._persist()
        return token, self._to_account(user)

    def get_user_by_token(self, token: Optional[str]) -> Optional[UserAccount]:
        if not token:
            return None
        user_id = self._sessions.get(token)
        if not user_id:
            return None
        for user in self._users.values():
            if user["id"] == user_id:
                return self._to_account(user)
        return None

    def link_vendor(self, user_id: str, vendor_id: str):
        for user in self._users.values():
            if user["id"] == user_id:
                user["role"] = UserRole.VENDOR.value
                user["vendor_id"] = vendor_id
                self._persist()
                return

    def _to_account(self, raw: Dict[str, Any]) -> UserAccount:
        return UserAccount(
            id=raw["id"],
            email=raw["email"],
            display_name=raw["display_name"],
            role=UserRole(raw["role"]),
            vendor_id=raw.get("vendor_id"),
            created_at=datetime.fromisoformat(raw["created_at"])
        )


auth_service = AuthService()


def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[UserAccount]:
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    return auth_service.get_user_by_token(token)


def require_user(authorization: Optional[str] = Header(None)) -> UserAccount:
    user = get_optional_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
