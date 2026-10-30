# Backend & Contract v1 Extract: NyayaLens

**Input Status:** **REPORT ONLY / SPECIFICATION-DEFINED** (Backend code not yet implemented; extracted from frozen Contract v1 and BE1/BE2 specifications).

---

## 1. API Endpoints Table (Contract v1)

Base URL: `/api/v1`

| Method | Path | Auth / Headers | Request Body / Query Params | Success Response (HTTP Status & Shape) | Error Responses | Status | Source Ref |
|---|---|---|---|---|---|---|---|
| `GET` | `/health` | None | None | `200 OK`<br>`{"status":"healthy","extraction_ready":true,"ocr_languages":["eng","hin","pan"],"model_ready":true,"tested_matrix":{"input":["en","hi","pa"],"output":["en","hi","pa"]}}` | None specified | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Public routes]` |
| `POST` | `/documents` | `Content-Type: multipart/form-data` | Multipart fields:<br>- `file` (binary, max 10MB, max 20 pages)<br>- `input_language` (`auto` \| `en` \| `hi` \| `pa`)<br>- `document_type` (`auto` \| `agreement` \| `fir` \| `notice` \| `other`) | `202 Accepted`<br>`{"document_id":"doc_123","session_token":"opaque_random_token","status":"extracting","revision":1}` | `400 FILE_TOO_LARGE`<br>`400 UNSUPPORTED_FILE`<br>`400 EMPTY_DOCUMENT` | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Extraction implementation]` |
| `GET` | `/documents/{document_id}` | `X-Session-Token: <token>` | Path: `document_id` | `200 OK`<br>`{"document_id":"...","status":"extracting"\|"awaiting_review"\|"queued"\|"analysing"\|"complete"\|"needs_review"\|"failed","revision":1,"filename":"...","document_type":"agreement","input_language":"en","warnings":[],"extraction_ready":true}` | `401 / 403 UNAUTHORIZED`<br>`404 NOT_FOUND` | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Session and privacy lifecycle]` |
| `GET` | `/documents/{document_id}/extraction` | `X-Session-Token: <token>` | Path: `document_id` | `200 OK`<br>`{"document_id":"...","revision":1,"document_type":"...","input_language":"...","clauses":[{"clause_id":"c1","source_text":"...","reviewed_text":"...","source_ref":{"page_number":1,"paragraph_index":null,"bbox":[x0,y0,x1,y1]},"extraction_method":"text"\|"ocr","review_required":false}],"warnings":[]}` | `409 EXTRACTION_NOT_READY`<br>`404 NOT_FOUND`<br>`500 EXTRACTION_FAILED` | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Public routes]` |
| `PATCH` | `/documents/{document_id}/extraction` | `X-Session-Token: <token>`<br>`Content-Type: application/json` | JSON Body:<br>`{"expected_revision":1,"corrections":[{"clause_id":"c1","text":"corrected text"}],"input_language":"en","document_type":"agreement"}` | `200 OK`<br>`{"document_id":"...","revision":2,"status":"awaiting_review","updated_at":"..."}` | `409 REVISION_CONFLICT`<br>`400 INVALID_CORRECTION`<br>`404 NOT_FOUND` | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Public routes]` |
| `GET` | `/documents/{document_id}/source` | `X-Session-Token: <token>` | Path: `document_id` | `200 OK`<br>Raw Binary Stream / Blob (`application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`) | `401 UNAUTHORIZED`<br>`404 NOT_FOUND` | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Session and privacy lifecycle]` |
| `POST` | `/documents/{document_id}/analyses` | `X-Session-Token: <token>`<br>`Content-Type: application/json` | JSON Body:<br>`{"expected_revision":2,"output_language":"hi"}` | `202 Accepted`<br>`{"analysis_id":"a1","status":"queued","document_revision":2}` | `409 REVISION_CONFLICT`<br>`503 MODEL_UNAVAILABLE`<br>`429 MODEL_BUSY` | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Async jobs]` |
| `GET` | `/documents/{document_id}/analyses/{analysis_id}` | `X-Session-Token: <token>` | Path: `document_id`, `analysis_id` | `200 OK`<br>`{"document_id":"...","analysis_id":"a1","status":"queued"\|"running"\|"complete"\|"needs_review"\|"failed","progress":{"completed_clauses":5,"total_clauses":10},"document_revision":2,"output_language":"hi","result":{...} \| null,"warnings":[]}` | `404 NOT_FOUND`<br>`500 ANALYSIS_FAILED` | PLANNED | `[R: 01-FE1 §Contract v1, 02-FE2 §Analysis and translation lifecycle]` |
| `POST` | `/documents/{document_id}/questions` | `X-Session-Token: <token>`<br>`Content-Type: application/json` | JSON Body:<br>`{"analysis_id":"a1","question":"...","output_language":"en","client_request_id":"uuid"}` | `200 OK`<br>`{"answer":"...","evidence":[{"clause_id":"c1","quote":"..."}],"reference_ids":[],"review_status":"supported"\|"needs_review","limitations":[]}` | `409 ANALYSIS_NOT_READY`<br>`429 MODEL_BUSY`<br>`504 MODEL_TIMEOUT`<br>`400 INVALID_QUESTION` | PLANNED | `[R: 01-FE1 §Contract v1, 02-FE2 §Questions and evidence]` |
| `DELETE` | `/documents/{document_id}` | `X-Session-Token: <token>` | Path: `document_id` | `204 No Content` | `404 NOT_FOUND` | PLANNED | `[R: 01-FE1 §Contract v1, 03-BE1 §Session and privacy lifecycle]` |

---

## 2. Shared Error Object Contract
Every HTTP error follows the frozen standard JSON shape:
```json
{
  "error": {
    "code": "EXTRACTION_FAILED",
    "message": "Readable explanation of failure",
    "retryable": false
  },
  "request_id": "req_123"
}
```
**Standard Error Codes:**
- `FILE_TOO_LARGE`: Exceeds 10MB or 20 PDF pages.
- `UNSUPPORTED_FILE`: Not a supported PDF or DOCX file.
- `EMPTY_DOCUMENT`: Zero bytes or no extractable text.
- `EXTRACTION_FAILED`: Document parsing parser threw an exception.
- `OCR_UNAVAILABLE`: Tesseract binary or language models missing on server.
- `EXTRACTION_NOT_READY`: Extraction still in progress (HTTP 409).
- `REVISION_CONFLICT`: Expected revision does not match current server revision (HTTP 409).
- `ANALYSIS_NOT_READY`: Analysis requested before extraction review or while queued (HTTP 409).
- `MODEL_UNAVAILABLE`: Local GPU / Qwen LLM not responding or offline (HTTP 503).
- `MODEL_BUSY`: GPU queue is saturated (HTTP 429).
- `MODEL_TIMEOUT`: Local generation exceeded timeout threshold (HTTP 504).
- `INVALID_MODEL_OUTPUT`: Output failed Pydantic schema validation.
- `NOT_FOUND`: Document or session deleted or expired (HTTP 404).
- `UNSUPPORTED_LANGUAGE`: Language detection cannot handle input script.

---

## 3. Real-Time & Event Architecture
- **WebSockets / SSE:** Explicitly **NOT** required / prohibited in Contract v1 ("No streaming requirement: upload returns immediately, FE1 polls extraction; FE2 polls analysis every 1–2 seconds and stops on completion, failure, deletion or unmount").
- **Polling Strategy:**
  - Extraction polling: `GET /documents/{document_id}` every 1–2s until `status` != `extracting`.
  - Analysis polling: `GET /documents/{document_id}/analyses/{analysis_id}` every 1–2s until terminal state (`complete`, `needs_review`, `failed`).
