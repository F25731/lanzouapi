from enum import Enum


class SourceStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class FileStatus(str, Enum):
    ACTIVE = "active"
    MISSING = "missing"
    DELETED = "deleted"


class ScanMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    RESCAN = "rescan"


class ScanJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ApiClientStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"


class AdminUserStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
