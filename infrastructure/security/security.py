"""
infrastructure/security/security.py
Sistema de permissões, auditoria e proteção de credenciais.
"""
from __future__ import annotations
from enum import Enum
from functools import wraps
from typing import Any, Callable
from infrastructure.logging.logger import logger


class Permission(str, Enum):
    """Permissões disponíveis no sistema."""
    CHAT = "chat"
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    DELETE_MEMORY = "delete_memory"
    GENERATE_IMAGE = "generate_image"
    VOICE = "voice"
    ADMIN = "admin"
    YOUTUBE_LEARN = "youtube_learn"
    PROGRAMMING = "programming"


# Perfis de permissão padrão
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "guest": {Permission.CHAT},
    "user": {
        Permission.CHAT,
        Permission.READ_MEMORY,
        Permission.WRITE_MEMORY,
        Permission.GENERATE_IMAGE,
        Permission.VOICE,
        Permission.YOUTUBE_LEARN,
        Permission.PROGRAMMING,
    },
    "admin": set(Permission),  # Todas as permissões
}


class SecurityManager:
    """Gerencia autenticação e autorização de usuários."""

    def __init__(self) -> None:
        self._user_roles: dict[str, str] = {}

    def assign_role(self, user_id: str, role: str) -> None:
        if role not in ROLE_PERMISSIONS:
            raise ValueError(f"Role inválida: {role}")
        self._user_roles[user_id] = role
        logger.info(f"[Security] user={user_id} assigned role={role}")

    def get_role(self, user_id: str) -> str:
        return self._user_roles.get(user_id, "user")

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        role = self.get_role(user_id)
        allowed = ROLE_PERMISSIONS.get(role, set())
        return permission in allowed

    def require_permission(self, permission: Permission) -> Callable:
        """Decorator que bloqueia execução sem permissão."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, user_id: str = "default", **kwargs: Any) -> Any:
                if not self.has_permission(user_id, permission):
                    logger.warning(
                        f"[Security] BLOCKED user={user_id} perm={permission.value}"
                    )
                    raise PermissionError(
                        f"Usuário '{user_id}' não tem permissão: {permission.value}"
                    )
                return await func(*args, user_id=user_id, **kwargs)
            return wrapper
        return decorator


def validate_env_secrets() -> list[str]:
    """
    Verifica que nenhuma credencial crítica está vazia.
    Retorna lista de variáveis ausentes.
    """
    import os
    required = ["MONGODB_URI", "GEMINI_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        logger.warning(f"[Security] Missing env vars: {missing}")
    return missing


# Singleton global
security_manager = SecurityManager()
