"""Environment-backed settings; no personal paths or credentials in defaults."""
import os
import math
from urllib.parse import urlparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import get_type_hints

@dataclass
class Settings:
    api_port: int = 8000
    web_origin: str = 'http://localhost:5173'
    ml_base_url: str = 'http://127.0.0.1:8001'
    ml_service_token: str = ''
    runtime_dir: Path = field(default_factory=lambda: Path('work/runtime/be1'))
    max_upload_mb: int = 25
    max_pdf_pages: int = 50
    session_ttl_minutes: float = 30
    model_timeout_seconds: float = 120
    ml_mode: str = 'real'
    inference_mode: str = 'local'
    extraction_workers: int = 2
    extraction_queue_size: int = 8
    extraction_timeout_seconds: float = 120
    extraction_memory_mb: int = 768
    max_docx_expanded_bytes: int = 50 * 1024 * 1024
    max_docx_entries: int = 2000
    max_extracted_chars: int = 500000
    ocr_timeout_seconds: float = 20
    ocr_max_pixels: int = 16000000
    poll_interval_seconds: float = 0.5
    max_analysis_jobs: int = 4
    cleanup_interval_seconds: float = 10
    max_analysis_seconds: float = 1800
    upload_rate_limit: int = 30

    def __post_init__(self):
        if self.inference_mode not in {'local','hosted'}:raise ValueError('INFERENCE_MODE must be local or hosted')
        # Preserve lexical path until SessionStore checks links/junctions.
        self.runtime_dir = Path(self.runtime_dir).absolute()
        if self.ml_mode not in {'real', 'fixture'}:
            raise ValueError('ML_MODE must be real or fixture')
        if not math.isfinite(self.max_analysis_seconds) or not math.isfinite(self.upload_rate_limit) or self.max_analysis_seconds <= 0 or self.upload_rate_limit <= 0:
            raise ValueError('Analysis budget and upload rate must be positive')
        for key in ('max_upload_mb','max_pdf_pages','session_ttl_minutes','model_timeout_seconds','extraction_workers','extraction_queue_size','extraction_timeout_seconds','extraction_memory_mb','max_docx_expanded_bytes','max_docx_entries','max_extracted_chars','ocr_timeout_seconds','ocr_max_pixels','poll_interval_seconds','max_analysis_jobs','cleanup_interval_seconds'):
            if not math.isfinite(getattr(self,key)) or getattr(self,key) <= 0:
                raise ValueError(f'{key} must be positive')
        if not 1 <= self.api_port <= 65535:
            raise ValueError('Invalid API_PORT')
        ml=urlparse(self.ml_base_url)
        if ml.scheme not in {'http','https'} or not ml.hostname or ml.username or ml.password or ml.query or ml.fragment:
            raise ValueError('ML_BASE_URL must be HTTP(S)')
        origin=urlparse(self.web_origin)
        if origin.scheme not in {'http','https'} or not origin.hostname or origin.path not in {'','/'} or origin.query or origin.fragment or origin.username or origin.password:
            raise ValueError('WEB_ORIGIN must be an explicit HTTP(S) origin')
        self.web_origin=self.web_origin.rstrip('/')

    @classmethod
    def from_env(cls):
        values = {}
        types=get_type_hints(cls)
        for name in cls.__dataclass_fields__:
            raw = os.getenv(name.upper())
            if raw is not None:
                values[name] = types[name](raw)
        return cls(**values)
