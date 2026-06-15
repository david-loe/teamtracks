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
    CLICK_CUE = "click_cue"
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


class ConversionJobType(StrEnum):
    STEM_CONVERSION = "stem_conversion"
    SONG_TRANSPOSITION = "song_transposition"
