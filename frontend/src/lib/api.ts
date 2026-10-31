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
  CapabilitiesResponse,
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
  ActionPackResponse,
  CompareRequest,
  CompareResponse,
  VerifySourceRequest,
  VerifySourceResponse,
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

export async function cancelAnalysis(documentId:string,sessionToken:string,analysisId:string):Promise<void> {
  try {
    const response=await fetch(`${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses/${encodeURIComponent(analysisId)}`,{
      method:'DELETE',headers:{'X-Session-Token':sessionToken},cache:'no-store',
    });
    await handleResponse<void>(response);
  } catch(error) {catchNetworkError(error);}
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
  // Refuse a development-mode backend rather than render simulated results.
  if(res.ok && data && typeof data==='object') {
    const items=Array.isArray(data.items)?data.items:Array.isArray(data.result?.items)?data.result.items:[];
    if(data.mode==='fixture' || data.__fixture===true || data.result?.__fixture===true || items.some((item: {detector?:string}|null) => item?.detector==='development_fixture')) {
      throw new ApiClientError(502,'SIMULATED_RESPONSE_REJECTED','This frontend requires real backend responses. Development-mode results are disabled.',false);
    }
  }

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
 * GET /capabilities
 */
export async function getCapabilities(signal?: AbortSignal): Promise<CapabilitiesResponse> {
  try {
    const res = await fetch(`${config.apiBaseUrl}/capabilities`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
      },
      signal,
    });
    return await handleResponse<CapabilitiesResponse>(res);
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
  signal?: AbortSignal,
  externalAiConsent = false
): Promise<DocumentCreateResponse> {
  try {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('input_language', inputLanguage);
    formData.append('document_type', documentType);
    formData.append('processing_consent', 'true');
    formData.append('external_ai_consent', String(externalAiConsent));

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

export async function downloadReviewReport(
  documentId: string, sessionToken: string, analysisId: string,
  format: 'json' | 'md' | 'html', includeQuestions = false
): Promise<Blob> {
  const url = `${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses/${encodeURIComponent(analysisId)}/report?format=${format}&include_questions=${includeQuestions}`;
  const response = await fetch(url, { headers: { 'X-Session-Token': sessionToken }, cache: 'no-store' });
  if (!response.ok) await handleResponse(response);
  return response.blob();
}

/**
 * 11. GET /documents/{id}/analyses/{analysis_id}/action-pack
 */
export async function getActionPack(
  documentId: string,
  sessionToken: string,
  analysisId: string,
  signal?: AbortSignal
): Promise<ActionPackResponse> {
  try {
    const res = await fetch(
      `${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses/${encodeURIComponent(analysisId)}/action-pack`,
      {
        method: 'GET',
        headers: {
          Accept: 'application/json',
          'X-Session-Token': sessionToken,
        },
        signal,
      }
    );
    return await handleResponse<ActionPackResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 12. POST /documents/{id}/compare
 */
export async function compareDocuments(
  documentIdA: string,
  sessionTokenA: string,
  documentIdB: string,
  sessionTokenB: string,
  revisionA: number,
  revisionB: number,
  signal?: AbortSignal
): Promise<CompareResponse> {
  try {
    const body: CompareRequest = {
      document_b_id: documentIdB,
      expected_revision_a: revisionA,
      expected_revision_b: revisionB,
    };
    const res = await fetch(
      `${config.apiBaseUrl}/documents/${encodeURIComponent(documentIdA)}/compare`,
      {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-Session-Token': sessionTokenA,
          'X-Compare-Session-Token': sessionTokenB,
        },
        body: JSON.stringify(body),
        signal,
      }
    );
    return await handleResponse<CompareResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

/**
 * 13. POST /documents/{id}/analyses/{analysis_id}/verify-source
 */
export async function verifySource(
  documentId: string,
  sessionToken: string,
  analysisId: string,
  externalAiConsent: boolean,
  signal?: AbortSignal
): Promise<VerifySourceResponse> {
  try {
    const body: VerifySourceRequest = {
      external_ai_consent: externalAiConsent,
    };
    const res = await fetch(
      `${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses/${encodeURIComponent(analysisId)}/verify-source`,
      {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          'X-Session-Token': sessionToken,
        },
        body: JSON.stringify(body),
        signal,
      }
    );
    return await handleResponse<VerifySourceResponse>(res);
  } catch (err) {
    return catchNetworkError(err);
  }
}

