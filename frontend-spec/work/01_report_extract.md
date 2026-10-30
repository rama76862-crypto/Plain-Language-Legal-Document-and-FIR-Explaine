# Report Extraction: NyayaLens (Plain Language Legal Document & FIR Explainer)

**Sources Analyzed:**
- `01-FRONTEND-1-App-Upload-Source.md` (`01-FE1`)
- `02-FRONTEND-2-Results-Evidence-Chat.md` (`02-FE2`)
- `03-BACKEND-1-API-Extraction-Sessions.md` (`03-BE1`)
- `04-BACKEND-2-Local-ML-Training-Languages.md` (`04-BE2`)

All 4 documents contain an identical "Shared project brief", "Product scope and multilingual truth", "Frozen architecture", "Contract v1", and "Safety and source rules".

---

## 1. Project Goal & Target Users
- **Project Goal:** Build NyayaLens for problem statement CTBF-AI-09: explain legal agreements, FIRs, and notices clause by clause in plain English, Hindi, or Punjabi, identify attention clauses and deadlines, cite source text, and link to official legal aid. [R: 01-FE1 §Shared project brief]
- **Nature of Product:** Hackathon prototype for consumer/citizen legal accessibility, strictly *not* a legal decision system or legal advice engine. [R: 01-FE1 §Shared project brief]
- **Target Users:** Indian citizens, consumers, tenants, or non-lawyers dealing with legal contracts, FIRs, or legal notices, needing explanations in English, Hindi (Devanagari), or Punjabi (Gurmukhi). [R: 01-FE1 §Product scope and multilingual truth]

---

## 2. Features & Capabilities

### Frontend 1 (FE1) Capabilities:
1. **Landing & Guidance:** Product purpose, temporary local processing disclosure, supported language status matrix. [R: 01-FE1 §User journey you implement]
2. **File Selection & Upload:** Upload PDF or DOCX; independent input language and answer language selection; document type selection (`auto`, `agreement`, `fir`, `notice`, `other`). [R: 01-FE1 §User journey you implement]
3. **Extraction Status Polling:** Real-time polling of extraction state (no fake progress bar). [R: 01-FE1 §User journey you implement]
4. **Original Source Viewer:** View authenticated PDF (via PDF.js/react-pdf) or DOCX numbered paragraphs/tables. [R: 01-FE1 §Data/state implementation details]
5. **Clause Review & Editing:** View extracted clauses; display scan/OCR warnings; inline human correction of clause text; PATCH corrections with optimistic revision control. [R: 01-FE1 §User journey you implement]
6. **Source Navigation & Evidence Highlighting:** Navigate to original source page/paragraph or bbox upon clause selection. [R: 01-FE1 §Data/state implementation details]
7. **Session Privacy & Deletion:** On-demand "Delete Session" and inactivity timer; revoke object URLs; wipe in-memory tokens. [R: 01-FE1 §Data/state implementation details]

### Frontend 2 (FE2) Capabilities:
1. **Results Workspace (`ResultsWorkspace`):** Analysis lifecycle orchestration, trigger analysis for reviewed revision. [R: 02-FE2 §Analysis and translation lifecycle]
2. **Real Work Progress:** Render actual `completed_clauses`/`total_clauses` progress. [R: 02-FE2 §Analysis and translation lifecycle]
3. **Clause-by-Clause Explanations:** Explains every clause in selected target language (`en`, `hi`, `pa`). Never silently omit ordinary clauses. [R: 02-FE2 §UX and behavior]
4. **Attention Cards:** Highlight potential concern categories (limitation of liability, unilateral termination/change, arbitration, penalty, automatic renewal); show why it matters, exact quote, and model/rule limitations. [R: 02-FE2 §UX and behavior]
5. **Deadlines & Timelines Panel:** Separate explicit dates from relative periods (e.g. "within 15 days of receipt") and flag missing anchor info. No calculated legal expiry dates in v1. [R: 02-FE2 §UX and behavior]
6. **Grounded Q&A Panel:** Document-scoped conversational questions; answers grounded strictly in document clauses; explicit refusal/insufficient evidence when outside scope. [R: 02-FE2 §Questions and evidence]
7. **Evidence Jump Link:** Click on evidence in any card or answer to trigger source viewer navigation in FE1. [R: 02-FE2 §UX and behavior]
8. **FIR & Notice Contextual Views:** Preserves allegations as allegations (never states guilt); notices show demanded action without advice to pay/sign. [R: 02-FE2 §UX and behavior]
9. **Official Legal Aid & Reference Links:** Static cards linking to official NALSA portal and verified statutory sections. [R: 02-FE2 §Questions and evidence]
10. **Export Report:** Client-side export to Markdown and Print; contains complete clause breakdown, timestamps, limitations, provenance, without session tokens or private URLs. [R: 02-FE2 §Export and privacy]

---

## 3. Screens & Views Identified
- **P-01: Landing & Upload View:** File dropzone/picker, document type dropdown, input language selector, target output language selector, temporary privacy disclaimer, language capability status pills. [R: 01-FE1 §User journey you implement]
- **P-02: Extraction & Processing View:** Extraction status banner, real extraction state, error/retry triggers. [R: 01-FE1 §User journey you implement]
- **P-03: Two-Pane Review Workspace (Split View):**
  - Left Pane: Original Document Viewer (PDF canvas / DOCX structure).
  - Right Pane (Phase 1): Extracted Clause Review list, edit inputs, OCR warnings, revision increment button ("Confirm Review & Analyse"). [R: 01-FE1 §User journey you implement]
- **P-04: Two-Pane Results Workspace (Split View):**
  - Left Pane: Original Document Viewer with evidence bounding box / page navigation active.
  - Right Pane (Phase 2): Results tabs (Overview, Clauses, Attention, Deadlines, Ask / Q&A, Export). [R: 02-FE2 §UX and behavior]
- **P-05: Error & Recovery Modals / Banners:** Revision conflict (409) modal, session expired (404) banner, model busy (429) retry prompt, connection lost banner. [R: 01-FE1 §Data/state implementation details, 02-FE2 §Integration examples and edge cases]
- **P-06: Session Cleanup Confirmation:** Modal/dialog to confirm session deletion and memory wipe. [R: 01-FE1 §User journey you implement]

---

## 4. API Contract Summary (Contract v1)
- `GET /health` -> System health, OCR languages, model readiness, tested language matrix. [R: 01-FE1 §Contract v1]
- `POST /documents` (multipart) -> Upload file, input/output language, doc type. Returns `document_id`, `session_token`, `status: extracting`, `revision: 1`. [R: 01-FE1 §Contract v1]
- `GET /documents/{document_id}` -> Document metadata, status, extraction_ready. Requires `X-Session-Token`. [R: 01-FE1 §Contract v1]
- `GET /documents/{document_id}/extraction` -> Original extracted clauses, warnings. Returns 409 if extracting. [R: 01-FE1 §Contract v1]
- `PATCH /documents/{document_id}/extraction` -> Submit edited clauses with `expected_revision`. Rejects stale revision with 409. [R: 01-FE1 §Contract v1]
- `GET /documents/{document_id}/source` -> Authenticated binary file download (Blob). Requires `X-Session-Token`. [R: 01-FE1 §Contract v1]
- `POST /documents/{document_id}/analyses` -> Start analysis for reviewed revision + output language. Returns `analysis_id`. [R: 01-FE1 §Contract v1]
- `GET /documents/{document_id}/analyses/{analysis_id}` -> Analysis progress (`completed_clauses`/`total_clauses`), status, result object. [R: 01-FE1 §Contract v1]
- `POST /documents/{document_id}/questions` -> Ask question scoped to analysis. Requires `client_request_id`. [R: 01-FE1 §Contract v1]
- `DELETE /documents/{document_id}` -> Delete session, source text, embeddings, results. Returns 204. [R: 01-FE1 §Contract v1]

---

## 5. Non-Functional & Safety Rules
- **Privacy & Security:** Keep session tokens in memory only. Never put documents/tokens in URLs, localStorage, cookies, or Git. Revoke Blob URLs on unmount/delete. [R: 01-FE1 §Data/state implementation details]
- **Multilingual Integrity:** English, Hindi (Devanagari), Punjabi (Gurmukhi). Input and output languages are independent. Changing output language never mutates original text. [R: 01-FE1 §Product scope and multilingual truth]
- **No Hallucinated Safety:** No "95% Safe" risk meters. Empty attention list means "No configured attention cues detected; review all clauses." [R: 02-FE2 §UX and behavior]
- **Legal Nuance:** FIRs contain allegations, not guilt. Notices state demanded action, not legal obligation to pay. Old laws retain old section numbers (no blind IPC to BNS remapping). [R: 01-FE1 §Safety and source rules]
- **Inactivity Timeout:** Disclosed 30-minute inactivity timer with visible countdown/reset. [R: 01-FE1 §Safety and source rules]
