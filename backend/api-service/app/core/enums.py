from enum import Enum

class QueryStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    transferring = "transferring"
    completed = "completed"
    failed = "failed" 