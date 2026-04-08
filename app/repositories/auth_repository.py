from __future__ import annotations

from datetime import datetime
from typing import List
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import AdminUser
from app.models.entities import ApiClient
from app.models.entities import ApiRequestLog
from app.models.enums import AdminUserStatus
from app.models.enums import ApiClientStatus


class ApiClientRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, client: ApiClient) -> ApiClient:
        self.db.add(client)
        self.db.flush()
        self.db.refresh(client)
        return client

    def get_by_id(self, client_id: int) -> Optional[ApiClient]:
        return self.db.query(ApiClient).filter(ApiClient.id == client_id).first()

    def get_by_name(self, client_name: str) -> Optional[ApiClient]:
        return (
            self.db.query(ApiClient)
            .filter(ApiClient.client_name == client_name)
            .first()
        )

    def get_by_key_prefix(self, key_prefix: str) -> Optional[ApiClient]:
        return (
            self.db.query(ApiClient)
            .filter(ApiClient.key_prefix == key_prefix)
            .first()
        )

    def list_clients(self) -> List[ApiClient]:
        return self.db.query(ApiClient).order_by(ApiClient.id.asc()).all()

    def touch_last_used(self, client: ApiClient) -> None:
        client.last_used_at = datetime.utcnow()
        self.db.add(client)
        self.db.flush()


class ApiRequestLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_log(
        self,
        client_id: Optional[int],
        request_path: str,
        request_method: str,
        request_ip: Optional[str],
        status_code: int,
        latency_ms: int,
    ) -> ApiRequestLog:
        log = ApiRequestLog(
            client_id=client_id,
            request_path=request_path,
            request_method=request_method,
            request_ip=request_ip,
            status_code=status_code,
            latency_ms=latency_ms,
        )
        self.db.add(log)
        self.db.flush()
        return log


class AdminUserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, admin_user: AdminUser) -> AdminUser:
        self.db.add(admin_user)
        self.db.flush()
        self.db.refresh(admin_user)
        return admin_user

    def get_by_id(self, admin_user_id: int) -> Optional[AdminUser]:
        return (
            self.db.query(AdminUser)
            .filter(AdminUser.id == admin_user_id)
            .first()
        )

    def get_by_username(self, username: str) -> Optional[AdminUser]:
        return (
            self.db.query(AdminUser)
            .filter(AdminUser.username == username)
            .first()
        )
