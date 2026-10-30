from __future__ import annotations

import pytest
from pydantic import ValidationError

from apps.ml.service.contracts import QuestionRequest


def test_private_question_limit_matches_public_contract_v1() -> None:
    base = {
        "document_id": "synthetic-document",
        "analysis_id": "synthetic-analysis",
        "document_revision": 1,
        "output_language": "en",
        "client_request_id": "synthetic-question",
    }

    request = QuestionRequest(**base, question="q" * 4000)

    assert len(request.question) == 4000
    with pytest.raises(ValidationError):
        QuestionRequest(**base, question="q" * 4001)
