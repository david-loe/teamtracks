from enum import StrEnum


class SongStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"
    ERROR = "error"


class StemRole(StrEnum):
    DRUMS = "drums"
    BASS = "bass"
    VOCALS = "vocals"
    GUITAR = "guitar"
    KEYS = "keys"
    OTHER = "other"


class StemStatus(StrEnum):
    UPLOADED = "uploaded"
    CONVERTING = "converting"
    READY = "ready"
    ERROR = "error"


class ConversionJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
