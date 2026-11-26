from enum import StrEnum


class Role(StrEnum):
    TECHNICIAN = "technician"
    SUPERVISOR = "supervisor"
    VIEWER = "viewer"


class Shift(StrEnum):
    DAWN = "dawn"
    DUSK = "dusk"


class PanelState(StrEnum):
    QUEUED = "queued"
    TRIAL = "trial"
    REJECTED = "rejected"
    ISSUED = "issued"
    ARCHIVED = "archived"


class TrialState(StrEnum):
    RECORDED = "recorded"
    APPROVED = "approved"
    RETURNED = "returned"
