/**
 * Accessibility helpers: evidence labels, focus management, screen-reader announcements
 */

export function getEvidenceAriaLabel(clauseId: string, pageNumber: number | null, paragraphIndex: number | null): string {
  if (pageNumber !== null) {
    return `View evidence for clause ${clauseId} on page ${pageNumber}`;
  }
  if (paragraphIndex !== null) {
    return `View evidence for clause ${clauseId} in paragraph ${paragraphIndex}`;
  }
  return `View evidence for clause ${clauseId}`;
}

export function announceToScreenReader(message: string, politeness: 'polite' | 'assertive' = 'polite'): void {
  const el = document.getElementById('a11y-announcer');
  if (el) {
    el.setAttribute('aria-live', politeness);
    el.textContent = message;
  }
}
