"""Authentication boundary for future account/cloud features.

V0.2 deliberately has no password database.  The desktop app runs as a local
guest; a future service can implement AuthProvider without changing advisor code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class UserSession:
    user_id: str
    display_name: str
    authenticated: bool
    access_token: str | None = None


class AuthProvider(Protocol):
    def current_session(self) -> UserSession: ...

    def sign_in(self, email: str, password: str) -> UserSession: ...

    def register(self, email: str, password: str) -> UserSession: ...

    def sign_out(self) -> None: ...


class LocalGuestAuth:
    """Safe V0.2 provider: no credentials are collected or persisted."""

    def current_session(self) -> UserSession:
        return UserSession("local-guest", "本地访客", False)

    def sign_in(self, email: str, password: str) -> UserSession:
        raise NotImplementedError("登录服务尚未启用；V0.2 不会在本地保存密码。")

    def register(self, email: str, password: str) -> UserSession:
        raise NotImplementedError("注册服务尚未启用；需要先部署正式认证后端。")

    def sign_out(self) -> None:
        return None
