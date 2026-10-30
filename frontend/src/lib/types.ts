/**
 * NyayaSarathi Contract v1 TypeScript Definitions
 * Single source of truth aligned exactly with Contract v1 specification.
 */

export type Language = 'en' | 'hi' | 'pa' | 'unknown';
export type InputLanguage = 'auto' | 'en' | 'hi' | 'pa';
export type OutputLanguage = 'en' | 'hi' | 'pa';

export type DocumentType = 'agreement' | 'fir' | 'notice' | 'other';
export type InputDocumentType = 'auto' | 'agreement' | 'fir' | 'notice' | 'other';

export type DocumentStatus =
  | 'extracting'
  | 'awaiting_review'
  | 'queued'
  | 'analysing'
  | 'complete'
  | 'needs_review'
  | 'failed';

export type AnalysisStatus =
  | 'queued'
  | 'running'
  | 'complete'
  | 'needs_review'
  | 'failed';

export type ResultItemKind =
  | 'explanation'
  | 'attention'
  | 'allegation'
  | 'notice_action';

export type ReviewStatus = 'supported' | 'needs_review';

export type DeadlineStatus = 'explicit' | 'needs_information' | 'needs_review';

export type DetectorType = 'rule' | 'model' | 'classifier' | 'extraction';

export type ExtractionMethod = 'text' | 'ocr';

export type ErrorCode =
  | 'FILE_TOO_LARGE'
  | 'UNSUPPORTED_FILE'
  | 'EMPTY_DOCUMENT'
  | 'EXTRACTION_FAILED'
  | 'OCR_UNAVAILABLE'
  | 'EXTRACTION_NOT_READY'
  | 'REVISION_CONFLICT'
  | 'ANALYSIS_NOT_READY'
  | 'MODEL_UNAVAILABLE'
  | 'MODEL_BUSY'
  | 'MODEL_TIMEOUT'
  | 'INVALID_MODEL_OUTPUT'
  | 'NOT_FOUND'
  | 'UNSUPPORTED_LANGUAGE'
  | 'INVALID_CORRECTION'
  | 'INVALID_QUESTION'
  | 'NETWORK_ERROR'
  | 'UNAUTHORIZED';

export interface ApiError {
  error: {
    code: ErrorCode | string;
    message: string;
    retryable: boolean;
  };
  request_id?: string;
}

export interface HealthResponse {
  status: string;
  extraction_ready: boolean;
  ocr_languages: string[];
  model_ready: boolean;
  tested_matrix: {
    input: string[];
    output: string[];
  };
}

export interface DocumentCreateResponse {
  document_id: string;
  session_token: string;
  status: DocumentStatus;
  revision: number;
  expires_at?: string;
}

export interface DocumentSummary {
  document_id: string;
  status: DocumentStatus;
  revision: number;
  filename: string;
  document_type: DocumentType;
  input_language: Language;
  warnings: string[];
  extraction_ready: boolean;
  reviewed_revision?: number | null;
  expires_at?: string;
}

export interface SourceRef {
  page_number: number | null; // 1-based for PDF; null for DOCX
  paragraph_index: number | null; // 1-based for DOCX; null for PDF
  bbox: [number, number, number, number] | null; // [x0, y0, x1, y1] PyMuPDF points, origin top-left
}

export interface Clause {
  clause_id: string;
  source_text: string;
  reviewed_text: string;
  source_ref: SourceRef;
  extraction_method: ExtractionMethod;
  review_required: boolean;
}

export interface ExtractionResponse {
  document_id: string;
  revision: number;
  document_type: DocumentType;
  input_language: Language;
  clauses: Clause[];
  warnings: string[];
}

export interface ClauseCorrection {
  clause_id: string;
  text: string;
}

export interface PatchRequest {
  expected_revision: number;
  corrections: ClauseCorrection[];
  input_language?: Language;
  document_type?: DocumentType;
}

export interface PatchResponse {
  document_id: string;
  revision: number;
  status: DocumentStatus;
  updated_at?: string;
}

export interface AnalysisCreateRequest {
  expected_revision: number;
  output_language: OutputLanguage;
}

export interface AnalysisCreateResponse {
  analysis_id: string;
  status: AnalysisStatus;
  document_revision: number;
}

export interface EvidenceRef {
  clause_id: string;
  quote: string;
}

export interface ResultItem {
  item_id: string;
  clause_id: string;
  kind: ResultItemKind;
  category: string | null;
  explanation: string;
  evidence: EvidenceRef[];
  reference_ids: string[];
  review_status: ReviewStatus;
  detector: DetectorType;
  model_score: number | null;
  limitations: string[];
}

export interface DeadlineItem {
  deadline_id: string;
  clause_id: string;
  source_quote: string;
  display_text: string;
  anchor: string | null;
  resolved_date: string | null;
  status: DeadlineStatus;
  missing_information: string[];
}

export interface LegalAidLink {
  title: string;
  url: string;
}

export interface Reference {
  reference_id: string;
  title: string;
  url: string;
  section: string;
  version: string;
  excerpt: string;
}

export interface Provenance {
  classifier_version: string;
  generator: string;
  rules_version: string;
}

export interface ResultCoverage {
  analysed: number;
  total: number;
}

export interface ResultObject {
  document_id: string;
  analysis_id: string;
  document_revision: number;
  input_language: Language;
  output_language: OutputLanguage;
  document_type: DocumentType;
  coverage: ResultCoverage;
  items: ResultItem[];
  deadlines: DeadlineItem[];
  warnings: string[];
  legal_aid: LegalAidLink[];
  references?: Reference[];
  document_profile?: string | null;
  structured_facts?: Record<string, unknown>[];
  next_steps?: {kind: string; text: string; clause_ids?: string[]; review_status?: string}[];
  provenance: Provenance;
}

export interface AnalysisProgress {
  completed_clauses: number;
  total_clauses: number;
  stage?: string | null;
  failed_clauses?: number;
}

export interface AnalysisStatusResponse {
  document_id: string;
  analysis_id: string;
  status: AnalysisStatus;
  progress: AnalysisProgress;
  document_revision: number;
  output_language: OutputLanguage;
  result: ResultObject | null;
  warnings: string[];
}

export interface QuestionRequest {
  analysis_id: string;
  question: string;
  output_language: OutputLanguage;
  client_request_id: string; // UUIDv4
}

export interface QuestionAnswer {
  answer: string;
  evidence: EvidenceRef[];
  reference_ids: string[];
  review_status: ReviewStatus;
  limitations: string[];
}

export interface ResultsWorkspaceProps {
  documentId: string;
  sessionToken: string;
  revision: number;
  outputLanguage: OutputLanguage;
  onNavigateEvidence: (clauseId: string) => void;
  onDeleted: () => void;
}
