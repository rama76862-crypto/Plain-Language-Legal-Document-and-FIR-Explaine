"""Shared public contract primitives owned by the API coordinator."""
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

Language = Literal['en', 'hi', 'pa', 'unknown']
OutputLanguage = Literal['en', 'hi', 'pa']
DocumentType = Literal['agreement', 'fir', 'notice', 'other']

class ApiError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, retryable: bool = False):
        self.code, self.message, self.status, self.retryable = code, message, status, retryable
        super().__init__(code)

class ContractModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class SourceRef(ContractModel):
    page_number: int | None = Field(default=None, ge=1)
    paragraph_index: int | None = Field(default=None, ge=1)
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)

class Clause(ContractModel):
    clause_id: str
    source_text: str
    reviewed_text: str
    source_ref: SourceRef
    extraction_method: str = 'text'
    review_required: bool = False

class Correction(ContractModel):
    clause_id: str
    text: str = Field(min_length=1, max_length=100000)

class ReviewRequest(ContractModel):
    expected_revision: int = Field(ge=1)
    corrections: list[Correction] = Field(default_factory=list, max_length=5000)
    input_language: Literal['en', 'hi', 'pa']
    document_type: DocumentType

class AnalysisRequest(ContractModel):
    expected_revision: int = Field(ge=1)
    output_language: OutputLanguage

class QuestionRequest(ContractModel):
    analysis_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=4000)
    output_language: OutputLanguage
    client_request_id: str = Field(min_length=1, max_length=128)

    @field_validator('question','client_request_id')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():
            raise ValueError('Value must not be blank')
        return value

class ErrorDetail(ContractModel):
    code: str
    message: str
    retryable: bool

class ErrorResponse(ContractModel):
    error: ErrorDetail
    request_id: str

class UploadAccepted(ContractModel):
    document_id: str
    session_token: str
    status: Literal['extracting']
    revision: int

class Metadata(ContractModel):
    document_id: str
    status: Literal['extracting','awaiting_review','queued','analysing','complete','needs_review','failed']
    revision: int
    filename: str
    document_type: Literal['auto','agreement','fir','notice','other']
    input_language: Literal['auto','en','hi','pa','unknown']
    warnings: list[str]
    extraction_ready: bool
    reviewed_revision: int | None
    expires_at: str
    progress: dict[str,Any]

class ExtractionResponse(ContractModel):
    document_id: str
    revision: int
    reviewed_revision: int | None
    clauses: list[Clause]
    warnings: list[str]
    input_language: Literal['auto','en','hi','pa','unknown']
    document_type: Literal['auto','agreement','fir','notice','other']
    progress: dict[str,Any]

class ReviewResponse(ContractModel):
    document_id: str
    revision: int
    reviewed_revision: int
    status: str
    changed: bool

class AnalysisAccepted(ContractModel):
    analysis_id: str
    status: Literal['queued','running','complete','needs_review']
    document_revision: int

class HealthResponse(ContractModel):
    status: Literal['ok','degraded']
    mode: Literal['real','fixture']
    extraction: dict[str,Any]
    ml: dict[str,Any]
    cleanup: dict[str,Any]
