"""API v1 response schemas."""

from api.v1.schemas.bills import (
    BillResponse,
    BillDetailResponse,
    BillListResponse
)
from api.v1.schemas.politicians import (
    PoliticianResponse,
    PoliticianListResponse
)
from api.v1.schemas.votes import (
    VoteResponse,
    VoteDetailResponse,
    VoteRecordResponse,
    VoteListResponse
)
from api.v1.schemas.debates import (
    DebateResponse,
    DebateListResponse,
    SpeechResponse
)

__all__ = [
    "BillResponse",
    "BillDetailResponse",
    "BillListResponse",
    "PoliticianResponse",
    "PoliticianListResponse",
    "VoteResponse",
    "VoteDetailResponse",
    "VoteRecordResponse",
    "VoteListResponse",
    "DebateResponse",
    "DebateListResponse",
    "SpeechResponse",
]
