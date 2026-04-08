from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.core.errors import ForbiddenError
from app.core.errors import NotFoundError
from app.core.errors import UnauthorizedError
from app.models.entities import AdminUser
from app.models.entities import ApiClient
from app.models.enums import AdminUserStatus
from app.models.enums import ApiClientStatus
from app.repositories.auth_repository import AdminUserRepository
from app.repositories.auth_repository import ApiClientRepository
from app.security.api_keys import extract_key_prefix
from app.security.api_keys import generate_api_key
from app.security.hashing import hash_secret
from app.security.hashing import verify_secret
from app.security.jwt_tools import create_admin_access_token
from app.utils.scopes import dump_ip_whitelist
from app.utils.scopes import dump_scopes
from app.utils.scopes import parse_ip_whitelist
from app.utils.scopes import parse_scopes


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.api_client_repository = ApiClientRepository(db)
        self.admin_user_repository = AdminUserRepository(db)

    def create_api_client(
        self,
        client_name: str,
        client_type: str,
        scopes: List[str],
        rate_limit_per_min: int,
        ip_whitelist: List[str],
    ) -> tuple[ApiClient, str]:
        if self.api_client_repository.get_by_name(client_name):
            raise ConflictError("api client name already exists")

        key_prefix, plain_key = generate_api_key()
        client = ApiClient(
            client_name=client_name,
            client_type=client_type,
            key_prefix=key_prefix,
            api_key_hash=hash_secret(plain_key),
            status=ApiClientStatus.ACTIVE,
            scopes=dump_scopes(scopes),
            rate_limit_per_min=rate_limit_per_min,
            ip_whitelist=dump_ip_whitelist(ip_whitelist),
        )
        self.api_client_repository.save(client)
        return client, plain_key

    def rotate_api_client_key(self, client_id: int) -> tuple[ApiClient, str]:
        client = self.get_api_client_or_raise(client_id)
        key_prefix, plain_key = generate_api_key()
        client.key_prefix = key_prefix
        client.api_key_hash = hash_secret(plain_key)
        self.api_client_repository.save(client)
        return client, plain_key

    def set_api_client_status(self, client_id: int, enabled: bool) -> ApiClient:
        client = self.get_api_client_or_raise(client_id)
        client.status = (
            ApiClientStatus.ACTIVE if enabled else ApiClientStatus.DISABLED
        )
        return self.api_client_repository.save(client)

    def list_api_clients(self) -> List[ApiClient]:
        return self.api_client_repository.list_clients()

    def authenticate_api_key(self, api_key: str, request_ip: str | None) -> ApiClient:
        key_prefix = extract_key_prefix(api_key)
        if not key_prefix:
            raise UnauthorizedError("invalid api key", code=40120)

        client = self.api_client_repository.get_by_key_prefix(key_prefix)
        if client is None:
            raise UnauthorizedError("invalid api key", code=40120)
        if client.status != ApiClientStatus.ACTIVE:
            raise ForbiddenError("api client disabled", code=40320)
        if not verify_secret(api_key, client.api_key_hash):
            raise UnauthorizedError("invalid api key", code=40120)

        whitelist = parse_ip_whitelist(client.ip_whitelist)
        if whitelist and request_ip and request_ip not in whitelist:
            raise ForbiddenError("ip not allowed", code=40321)

        self.api_client_repository.touch_last_used(client)
        return client

    def ensure_client_scopes(
        self,
        client: ApiClient,
        required_scopes: List[str],
    ) -> None:
        if not required_scopes:
            return
        client_scopes = set(parse_scopes(client.scopes))
        missing = [scope for scope in required_scopes if scope not in client_scopes]
        if missing:
            raise ForbiddenError(
                "missing scopes: {0}".format(", ".join(missing)),
                code=40322,
            )

    def get_api_client_or_raise(self, client_id: int) -> ApiClient:
        client = self.api_client_repository.get_by_id(client_id)
        if client is None:
            raise NotFoundError("api client not found", code=40420)
        return client

    def create_admin_user(self, username: str, password: str) -> AdminUser:
        if self.admin_user_repository.get_by_username(username):
            raise ConflictError("admin username already exists")
        admin_user = AdminUser(
            username=username,
            password_hash=hash_secret(password),
            status=AdminUserStatus.ACTIVE,
        )
        return self.admin_user_repository.save(admin_user)

    def authenticate_admin_user(self, username: str, password: str) -> tuple[AdminUser, str]:
        admin_user = self.admin_user_repository.get_by_username(username)
        if admin_user is None:
            raise UnauthorizedError("invalid username or password", code=40130)
        if admin_user.status != AdminUserStatus.ACTIVE:
            raise ForbiddenError("admin user disabled", code=40330)
        if not verify_secret(password, admin_user.password_hash):
            raise UnauthorizedError("invalid username or password", code=40130)
        admin_user.last_login_at = datetime.utcnow()
        self.admin_user_repository.save(admin_user)
        token = create_admin_access_token(admin_user.username, admin_user.id)
        return admin_user, token

    def get_admin_user_or_raise(self, admin_user_id: int) -> AdminUser:
        admin_user = self.admin_user_repository.get_by_id(admin_user_id)
        if admin_user is None:
            raise UnauthorizedError("admin user not found", code=40131)
        if admin_user.status != AdminUserStatus.ACTIVE:
            raise ForbiddenError("admin user disabled", code=40330)
        return admin_user
