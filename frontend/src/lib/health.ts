import type { HealthResponse } from './types';

function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown> : {};
}

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : [];
}

/** Adapt the public BE1 health contract; missing evidence never implies readiness. */
export function normalizeHealth(value: unknown): HealthResponse {
  const data = record(value);
  const extraction = record(data.extraction);
  const ocr = record(extraction.ocr);
  const ml = record(data.ml);
  return {
    status: typeof data.status === 'string' ? data.status : 'unknown',
    extraction_ready: extraction.ready === true,
    ocr_languages: ocr.available === true ? strings(ocr.languages) : [],
    model_ready: data.mode === 'real' && ml.available === true,
    // Independent input/output lists cannot establish a reviewed 3x3 matrix.
    tested_matrix: { input: [], output: [] },
  };
}
