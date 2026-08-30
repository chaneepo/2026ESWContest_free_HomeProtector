from enum import StrEnum


class RoutineType(StrEnum):
    OUTING_PREP = "OUTING_PREP"
    RETURN_HOME = "RETURN_HOME"


class JobMode(StrEnum):
    SIMULATION = "SIMULATION"
    REAL = "REAL"


class JobStatus(StrEnum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class JobStep(StrEnum):
    IDLE = "IDLE"
    PLAN = "PLAN"
    DETECT = "DETECT"
    PICK = "PICK"
    MOVE = "MOVE"
    PLACE = "PLACE"
    VERIFY = "VERIFY"
    RECOVER = "RECOVER"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class JobItemStatus(StrEnum):
    WAITING = "WAITING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class EventDevice(StrEnum):
    SYSTEM = "SYSTEM"
    VISION = "VISION"
    ARM = "ARM"
    ESP32 = "ESP32"
    RAZBOT = "RAZBOT"


class EventSeverity(StrEnum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"
