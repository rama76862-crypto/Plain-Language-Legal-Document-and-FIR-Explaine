/**
 * EvidenceButton Component
 * Accessible button triggering source viewer navigation:
 * - Emits onNavigateEvidence(clauseId)
 * - Sets accessible aria-label naming clause ID and location
 * - Carries data-evidence-source="active" when active
 */

import React from 'react';
import { Eye } from 'lucide-react';
import { getEvidenceAriaLabel } from '../../lib/a11y';

interface EvidenceButtonProps {
  clauseId: string;
  pageNumber?: number | null;
  paragraphIndex?: number | null;
  onNavigateEvidence: (clauseId: string) => void;
  isActive?: boolean;
  className?: string;
}

export const EvidenceButton: React.FC<EvidenceButtonProps> = ({
  clauseId,
  pageNumber = null,
  paragraphIndex = null,
  onNavigateEvidence,
  isActive = false,
  className = '',
}) => {
  const ariaLabel = getEvidenceAriaLabel(clauseId, pageNumber, paragraphIndex);

  return (
    <button
      type="button"
      data-evidence-source={isActive ? 'active' : undefined}
      onClick={(e) => {
        e.stopPropagation();
        onNavigateEvidence(clauseId);
      }}
      aria-label={ariaLabel}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded font-mono transition-all ${
        isActive
          ? 'bg-blue text-white shadow-sm ring-2 ring-cyan'
          : 'bg-paper text-navy border border-line hover:bg-bg2 hover:border-blue/40'
      } ${className}`}
    >
      <Eye className="w-3.5 h-3.5 text-cyan shrink-0" aria-hidden="true" />
      <span>View evidence ({clauseId})</span>
    </button>
  );
};
export default EvidenceButton;
