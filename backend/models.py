from pydantic import BaseModel, validator
from typing import Optional, Dict, Any
import time


class EventMetadata(BaseModel):
    file: Optional[str] = None
    status: Optional[str] = "success"  # "success" | "failure"

    class Config:
        extra = "allow"


class Event(BaseModel):
    session_id: str
    timestamp: Optional[float] = None
    step: Optional[int] = None
    action: Optional[str] = None
    input: Optional[str] = ""
    output: Optional[str] = ""
    metadata: Optional[EventMetadata] = None

    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        return v if v is not None else time.time()

    @validator("metadata", pre=True, always=True)
    def set_metadata(cls, v):
        if v is None:
            return EventMetadata()
        if isinstance(v, dict):
            return EventMetadata(**{k: val for k, val in v.items() if k in EventMetadata.__fields__})
        return v

    @validator("action", pre=True, always=True)
    def validate_action(cls, v):
        valid = {"read_file", "write_file", "run_command", "llm_call"}
        return v if v in valid else "unknown"
