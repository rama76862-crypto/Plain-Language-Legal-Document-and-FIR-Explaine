/**
 * Typed Fetch API Client for NyayaSarathi (Contract v1)
 * Adheres strictly to security and privacy guidelines:
 * - Never logs request bodies, tokens, or document content
 * - Sends X-Session-Token header when provided
 * - Leaves Content-Type unset for multipart/form-data
 * - Decodes shared error schema into typed ApiClientError
 */

import { config } from './config';
import { normalizeHealth } from './health';
import type {
  HealthResponse,
  DocumentCreateResponse,
  DocumentSummary,
  ExtractionResponse,
  PatchRequest,
  PatchResponse,
  AnalysisCreateRequest,
  AnalysisCreateResponse,
  AnalysisStatusResponse,
  QuestionRequest,
  QuestionAnswer,
  ErrorCode,
  ApiError,
  InputLanguage,
  InputDocumentType,
} from './types';

export class ApiClientError extends Error {
  status: number;
  code: ErrorCode | string;
  override message: string;
  retryable: boolean;
  requestId?: string;

  constructor(status: number, code: ErrorCode | string, message: string, retryable: boolean, requestId?: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.message = message;
    this.retryable = retryable;
    this.requestId = requestId;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    return {} as T;
  }

  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    if (!res.ok) {
      throw new ApiClientError(
        res.status,
        res.status >= 500 ? 'NETWORK_ERROR' : 'UNKNOWN_ERROR',
        `Server returned ${res.status}: ${res.statusText}`,
        res.status >= 500
      );
    }
    return {} as T;
  }

  const data = await res.json();

  if (!res.ok) {
    const errorBody = data as ApiError;
    const err = errorBody?.error;
    throw new ApiClientError(
      res.status,
      err?.code || 'UNKNOWN_ERROR',
      err?.message || `Request failed with HTTP ${res.status}`,
      err?.retryable ?? (res.status >= 500 || res.status === 429),
      errorBody?.request_id
    );
  }

  return data as T;
}

function catchNetworkError(err: unknown): never {
  if (err instanceof ApiClientError) {
    throw err;
  }
  if (err instanceof DOMException && err.name === 'AbortError') {
    throw err;
  }
  const msg = err instanceof Error ? err.message : 'Network request failed';
  throw new ApiClientError(0, 'NETWORK_ERROR', msg, true);
}

/**
 * 1. GET /health
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/health`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });
    return normalizeHealth(await handleResponse<unknown>(res));
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 2. POST /documents (multipart)
 * Notice: Browser automatically sets Content-Type with boundary.
 */
export async function createDocument(
  file: File,
  inputLanguage: InputLanguage,
  documentType: InputDocumentType,
  signal?: AbortSignal
): Promise<DocumentCreateResponse> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('input_language', inputLanguage);
    formData.append('document_type', documentType);

    const res = await fetch(`${config.apiBaseUrl}/documents`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
      },
      body: formData,
      signal,
    });
    return await handleResponse<DocumentCreateResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 3. GET /documents/{id}
 */
export async function getDocument(
  documentId: string,
  sessionToken: string,
  signal?: AbortSignal
): Promise<DocumentSummary> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'X-Session-Token': sessionToken,
      },
      signal,
    });
    return await handleResponse<DocumentSummary>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 4. GET /documents/{id}/extraction
 */
export async function getExtraction(
  documentId: string,
  sessionToken: string,
  signal?: AbortSignal
): Promise<ExtractionResponse> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/extraction`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'X-Session-Token': sessionToken,
      },
      signal,
    });
    return await handleResponse<ExtractionResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 5. PATCH /documents/{id}/extraction
 */
export async function patchExtraction(
  documentId: string,
  sessionToken: string,
  patch: PatchRequest,
  signal?: AbortSignal
): Promise<PatchResponse> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/extraction`, {
      method: 'PATCH',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken,
      },
      body: JSON.stringify(patch),
      signal,
    });
    return await handleResponse<PatchResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 6. GET /documents/{id}/source
 * Fetches authenticated raw binary blob.
 */
export async function fetchSourceBlob(
  documentId: string,
  sessionToken: string,
  signal?: AbortSignal
): Promise<Blob> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/source`, {
      method: 'GET',
      headers: {
        'X-Session-Token': sessionToken,
      },
      signal,
    });

    if (!res.ok) {
      return await handleResponse<never>(res);
    }

    return await res.blob();
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 7. POST /documents/{id}/analyses
 */
export async function createAnalysis(
  documentId: string,
  sessionToken: string,
  req: AnalysisCreateRequest,
  signal?: AbortSignal
): Promise<AnalysisCreateResponse> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken,
      },
      body: JSON.stringify(req),
      signal,
    });
    return await handleResponse<AnalysisCreateResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 8. GET /documents/{id}/analyses/{analysis_id}
 */
export async function getAnalysis(
  documentId: string,
  analysisId: string,
  sessionToken: string,
  signal?: AbortSignal
): Promise<AnalysisStatusResponse> {
  try {
    const res = await fetch(
      `${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses/${encodeURIComponent(analysisId)}`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          'X-Session-Token': sessionToken,
        },
        signal,
      }
    );
    return await handleResponse<AnalysisStatusResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 9. POST /documents/{id}/questions
 */
export async function askQuestion(
  documentId: string,
  sessionToken: string,
  req: QuestionRequest,
  signal?: AbortSignal
): Promise<QuestionAnswer> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/questions`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Session-Token': sessionToken,
      },
      body: JSON.stringify(req),
      signal,
    });
    return await handleResponse<QuestionAnswer>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 10. DELETE /documents/{id}
 */
export async function deleteDocument(
  documentId: string,
  sessionToken: string,
  signal?: AbortSignal
): Promise<void> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
      headers: {
        'X-Session-Token': sessionToken,
      },
      signal,
    });
    await handleResponse<void>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}
