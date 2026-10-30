/**
 * EvidenceCard Component (C-09)
 * Renders an explanation or attention cue strictly anchored to source evidence:
 * - Location chip (p. X or ¶ Y)
 * - Original text with exact substring highlight
 * - Plain language explanation
 * - Potential concern category
 * - EvidenceButton
 * - Verified statutory references only
 * - Limitations and technical detector provenance
 * - FIR / Notice custom semantics
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Cpu,
  ShieldAlert,
  FileCheck,
  Scale,
} from 'lucide-react';
import type { ResultItem, Clause, Reference, OutputLanguage } from '../../lib/types';
import { EvidenceButton } from './EvidenceButton';
import { ReferenceCard } from './ReferenceCard';
import { MonoLabel } from '../../design/primitives';

interface EvidenceCardProps {
  item: ResultItem;
  clause?: Clause;
  outputLanguage: OutputLanguage;
  references?: Reference[];
  onNavigateEvidence: (clauseId: string) => void;
  isActive?: boolean;
  className?: string;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  item,
  clause,
  outputLanguage,
  references = [],
  onNavigateEvidence,
  isActive = false,
  className = '',
}) => {
  const isNeedsReview = item.review_status === 'needs_review';
  const [showOriginal, setShowOriginal] = useState<boolean>(isNeedsReview);
  const [showTechDetails, setShowTechDetails] = useState<boolean>(false);

  // Derive location
  const pageNum = clause?.source_ref.page_number;
  const paraIdx = clause?.source_ref.paragraph_index;
  const locationLabel = pageNum ? `p.${pageNum}` : paraIdx ? `¶ ${paraIdx}` : null;

  // Derive original text
  const originalText = clause?.reviewed_text || clause?.source_text || '';
  const firstQuote = item.evidence?.[0]?.quote || '';

  // Check if quote is a true substring of original text
  let isExactSubstring = false;
  let quotePrefix = '';
  let quoteMatched = '';
  let quoteSuffix = '';

  if (firstQuote && originalText) {
    const idx = originalText.indexOf(firstQuote);
    if (idx !== -1) {
      isExactSubstring = true;
      quotePrefix = originalText.substring(0, idx);
      quoteMatched = firstQuote;
      quoteSuffix = originalText.substring(idx + firstQuote.length);
    }
  }

  // Resolved references
  const resolvedReferences = (item.reference_ids || [])
    .map((refId) => references.find((r) => r.reference_id === refId))
    .filter((r): r is Reference => !!r);

  const unresolvedRefIds = (item.reference_ids || []).filter(
    (refId) => !references.some((r) => r.reference_id === refId)
  );

  // Human label for category
  const categoryLabel = item.category ? item.category.replace(/_/g, ' ') : null;

  // Language display name
  const langNames: Record<OutputLanguage, string> = {
    en: 'English',
    hi: 'हिन्दी',
    pa: 'ਪੰਜਾਬੀ',
  };

  return (
    <motion.div
      layout
      data-clause-id={item.clause_id}
      className={`rounded-lg border bg-paper transition-all p-5 space-y-4 shadow-card ${
        isActive
          ? 'ring-2 ring-cyan border-blue shadow-md'
          : item.kind === 'attention'
          ? 'border-amber-500/30 hover:border-amber-500/60'
          : 'border-line hover:border-blue/40'
      } ${className}`}
    >
      {/* 1. Header: Clause Chip + Location + Status */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-line">
        <div className="flex items-center gap-2">
          <MonoLabel>{item.clause_id}</MonoLabel>
          {locationLabel && (
            <span className="text-xs font-mono font-medium text-mute px-1.5 py-0.5 rounded bg-bg2">
              {locationLabel}
            </span>
          )}
          {clause?.extraction_method && (
            <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-bg2 text-mute">
              {clause.extraction_method}
            </span>
          )}
        </div>

        {/* Kind Header Tag */}
        <div className="flex items-center gap-2">
          {item.kind === 'allegation' ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-blue/10 text-blue">
              <Scale className="w-3 h-3" />
              Allegation recorded in FIR
            </span>
          ) : item.kind === 'notice_action' ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-blue/10 text-blue">
              <FileCheck className="w-3 h-3" />
              Action demanded by document
            </span>
          ) : item.kind === 'attention' ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-amber-500/10 text-amber-800">
              <ShieldAlert className="w-3 h-3" />
              Potential Concern: {categoryLabel}
            </span>
          ) : (
            <span className="text-[11px] font-mono font-medium text-mute uppercase">
              Standard Explanation
            </span>
          )}
        </div>
      </div>

      {/* Needs-Review Warning Banner */}
      {isNeedsReview && (
        <div className="flex items-start gap-2 p-2.5 rounded bg-amber-500/10 border border-amber-500/20 text-xs text-amber-900">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <span>
            Translation-assisted / Low confidence: Please verify against the original text.
          </span>
        </div>
      )}

      {/* 2. Original Text with Substring Highlight */}
      {originalText && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono uppercase text-mute font-medium">
              Original Text ({clause?.extraction_method === 'ocr' ? 'OCR' : 'Document'})
            </span>
            <button
              type="button"
              onClick={() => setShowOriginal(!showOriginal)}
              className="text-[11px] font-semibold text-blue hover:underline flex items-center gap-0.5"
            >
              <span>{showOriginal ? 'Collapse' : 'Show full original'}</span>
              {showOriginal ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          </div>

          <div
            className={`p-3 rounded-md bg-bg2/50 border border-line/70 font-serif text-xs text-navy leading-[1.7] ${
              showOriginal ? '' : 'line-clamp-2'
            }`}
          >
            {isExactSubstring ? (
              <span>
                <span>{quotePrefix}</span>
                <mark className="bg-cyan/30 text-navy font-semibold px-0.5 rounded-xs">
                  {quoteMatched}
                </mark>
                <span>{quoteSuffix}</span>
              </span>
            ) : (
              <span>{originalText}</span>
            )}
          </div>
        </div>
      )}

      {/* 3. Plain Language Explanation */}
      <div className="space-y-1">
        <span className="text-[11px] font-mono uppercase text-blue font-semibold">
          Explanation in {langNames[outputLanguage]}
        </span>
        <p className="text-sm font-medium text-navy leading-[1.7] whitespace-pre-line">
          {item.explanation}
        </p>
      </div>

      {/* 4. Evidence Navigation Button */}
      <div className="pt-1 flex flex-wrap items-center justify-between gap-3">
        <EvidenceButton
          clauseId={item.clause_id}
          pageNumber={pageNum}
          paragraphIndex={paraIdx}
          onNavigateEvidence={onNavigateEvidence}
          isActive={isActive}
        />

        {/* Limitations Pills */}
        {item.limitations && item.limitations.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {item.limitations.map((lim, idx) => (
              <span
                key={idx}
                className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-800 border border-amber-500/20"
              >
                {lim}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* 5. Verified Statutory References */}
      {resolvedReferences.length > 0 && (
        <div className="space-y-2 pt-2 border-t border-line">
          <span className="text-[11px] font-mono uppercase text-mute font-semibold">
            Verified Statutory References ({resolvedReferences.length})
          </span>
          <div className="space-y-2">
            {resolvedReferences.map((ref) => (
              <ReferenceCard key={ref.reference_id} reference={ref} />
            ))}
          </div>
        </div>
      )}

      {/* Unresolved reference warning (if any) */}
      {unresolvedRefIds.length > 0 && (
        <div className="text-[10px] font-mono text-mute pt-1">
          Reference unavailable: {unresolvedRefIds.join(', ')}
        </div>
      )}

      {/* 6. Technical Details Expander */}
      <div className="pt-1">
        <button
          type="button"
          onClick={() => setShowTechDetails(!showTechDetails)}
          className="text-[11px] font-mono text-mute hover:text-navy flex items-center gap-1"
        >
          <Cpu className="w-3 h-3 text-blue" />
          <span>Technical details</span>
          {showTechDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>

        {showTechDetails && (
          <div className="mt-2 p-2.5 rounded bg-bg2/40 border border-line text-[11px] font-mono space-y-1">
            <div>Detector engine: <strong className="text-navy">{item.detector}</strong></div>
            {item.model_score !== null && item.model_score !== undefined && (
              <div>
                Model score for this category: <strong className="text-navy">{item.model_score}</strong>{' '}
                <span className="text-mute">(not a probability of legal risk)</span>
              </div>
            )}
            <div>Clause status: <strong className="text-navy">{item.review_status}</strong></div>
          </div>
        )}
      </div>
    </motion.div>
  );
};
export default EvidenceCard;
