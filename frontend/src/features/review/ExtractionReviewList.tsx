/**
 * ExtractionReviewList Component (C-06)
 * Right pane of the review workspace:
 * - Displays all extracted clauses with OCR flags
 * - Manages in-memory correction buffer Record<clauseId, string>
 * - Enforces optimistic revision control on submittal
 * - Displays actionable review warnings
 */

import React, { useState } from 'react';
import type { Clause, DocumentType, Language, OutputLanguage, PatchRequest } from '../../lib/types';
import { ClauseReviewCard } from './ClauseReviewCard';
import { Button, Banner, MonoLabel, Select } from '../../design/primitives';
import { useT } from '../../lib/i18n';
import { CheckCircle2, AlertTriangle, Send } from 'lucide-react';

interface ExtractionReviewListProps {
  clauses: Clause[];
  revision: number;
  warnings: string[];
  filename?: string | null;
  inputLanguage: Language;
  outputLanguage: OutputLanguage;
  documentType: DocumentType;
  selectedClauseId?: string | null;
  isSubmitting?: boolean;
  saveError?: { title: string; message: string; retryable?: boolean } | null;
  onSelectClause: (clauseId: string) => void;
  onSubmitReview: (patch: PatchRequest) => void;
  onChangeInputLanguage: (lang: Language) => void;
  onChangeOutputLanguage: (lang: OutputLanguage) => void;
  onChangeDocumentType: (type: DocumentType) => void;
}

export const ExtractionReviewList: React.FC<ExtractionReviewListProps> = ({
  clauses,
  revision,
  warnings,
  inputLanguage,
  outputLanguage,
  documentType,
  selectedClauseId,
  isSubmitting = false,
  saveError = null,
  onSelectClause,
  onSubmitReview,
  onChangeInputLanguage,
  onChangeOutputLanguage,
  onChangeDocumentType,
}) => {
  const { t } = useT();

  // In-memory corrections buffer: clause_id -> corrected text
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [confirmedChecked, setConfirmedChecked] = useState(false);
  const [activeFilter, setActiveFilter] = useState<'all' | 'needs_review' | 'ocr' | 'edited'>('all');

  const textCount = clauses.filter((c) => c.extraction_method !== 'ocr').length;
  const ocrCount = clauses.filter((c) => c.extraction_method === 'ocr').length;
  const reviewRequiredCount = clauses.filter((c) => c.review_required).length;
  const editedCount = Object.keys(corrections).length;

  const displayedClauses = clauses.filter((c) => {
    if (activeFilter === 'needs_review') return c.review_required;
    if (activeFilter === 'ocr') return c.extraction_method === 'ocr';
    if (activeFilter === 'edited') return corrections[c.clause_id] !== undefined;
    return true;
  });

  const handleSaveCorrection = (clauseId: string, newText: string) => {
    setCorrections((prev) => ({
      ...prev,
      [clauseId]: newText,
    }));
  };

  const handleResetCorrection = (clauseId: string) => {
    setCorrections((prev) => {
      const copy = { ...prev };
      delete copy[clauseId];
      return copy;
    });
  };

  const handleConfirmSubmit = () => {
    const correctionList = Object.entries(corrections).map(([clause_id, text]) => ({
      clause_id,
      text,
    }));

    onSubmitReview({
      expected_revision: revision,
      corrections: correctionList,
      input_language: inputLanguage,
      document_type: documentType,
    });
  };

  return (
    <div className="flex flex-col h-full bg-paper overflow-y-auto p-6 space-y-6">
      {/* Top Header Summary */}
      <div className="space-y-4 pb-4 border-b border-line">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <MonoLabel>EXTRACTION REVIEW</MonoLabel>
            <h2 className="text-xl font-extrabold text-navy tracking-tight mt-0.5">
              {t('review.title')}
            </h2>
            <p className="text-xs text-mute mt-1">{t('review.sub')}</p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2.5 py-1 rounded bg-navy text-white font-mono text-xs font-bold">
              {t('review.revisionLabel', { rev: revision })}
            </span>
            <span className="px-2.5 py-1 rounded bg-bg2 text-navy font-mono text-xs font-semibold">
              {t('review.clauseCount', { count: clauses.length })}
            </span>
          </div>
        </div>

        {/* Telemetry Chips & Language Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
          <Select
            label={t('upload.docLanguageLabel')}
            value={inputLanguage}
            onChange={(val) => onChangeInputLanguage(val as Language)}
            options={[
              { value: 'en', label: 'English' },
              { value: 'hi', label: 'हिन्दी (Hindi)' },
              { value: 'pa', label: 'ਪੰਜਾਬੀ (Punjabi)' },
            ]}
          />
          <Select
            label={t('upload.explainInLabel')}
            value={outputLanguage}
            onChange={(val) => onChangeOutputLanguage(val as OutputLanguage)}
            options={[
              { value: 'en', label: 'English' },
              { value: 'hi', label: 'हिन्दी (Hindi)' },
              { value: 'pa', label: 'ਪੰਜਾਬੀ (Punjabi)' },
            ]}
          />
          <Select
            label={t('upload.docTypeLabel')}
            value={documentType}
            onChange={(val) => onChangeDocumentType(val as DocumentType)}
            options={[
              { value: 'agreement', label: t('docTypes.agreement') },
              { value: 'fir', label: t('docTypes.fir') },
              { value: 'notice', label: t('docTypes.notice') },
              { value: 'other', label: t('docTypes.other') },
            ]}
          />
        </div>

        {/* Filter Chips Bar */}
        <div className="flex flex-wrap items-center gap-2 pt-2">
          <button
            type="button"
            onClick={() => setActiveFilter('all')}
            className={`px-3 py-1 rounded-pill text-xs font-semibold transition-all ${
              activeFilter === 'all'
                ? 'bg-navy text-white shadow-sm'
                : 'bg-bg2 text-mute hover:text-navy hover:bg-bg2/80'
            }`}
          >
            {t('results.filterAll', { count: clauses.length })}
          </button>
          {reviewRequiredCount > 0 && (
            <button
              type="button"
              onClick={() => setActiveFilter('needs_review')}
              className={`px-3 py-1 rounded-pill text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeFilter === 'needs_review'
                  ? 'bg-caution text-navy font-bold shadow-sm'
                  : 'bg-caution-bg text-caution-ink hover:opacity-90'
              }`}
            >
              <AlertTriangle className="w-3 h-3 text-caution" />
              <span>{t('review.reviewRequiredCount', { count: reviewRequiredCount })}</span>
            </button>
          )}
          {ocrCount > 0 && (
            <button
              type="button"
              onClick={() => setActiveFilter('ocr')}
              className={`px-3 py-1 rounded-pill text-xs font-semibold transition-all ${
                activeFilter === 'ocr'
                  ? 'bg-cyan text-navy font-bold shadow-sm'
                  : 'bg-deadline-bg text-deadline-ink hover:opacity-90'
              }`}
            >
              <span>{t('review.breakdownOcr', { count: ocrCount })}</span>
            </button>
          )}
          {editedCount > 0 && (
            <button
              type="button"
              onClick={() => setActiveFilter('edited')}
              className={`px-3 py-1 rounded-pill text-xs font-semibold transition-all ${
                activeFilter === 'edited'
                  ? 'bg-ok text-white font-bold shadow-sm'
                  : 'bg-ok-bg text-ok-ink hover:opacity-90'
              }`}
            >
              <span>{t('review.editedBadge')} ({editedCount})</span>
            </button>
          )}
        </div>

        {/* Text vs OCR Breakdown Telemetry */}
        <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-mute pt-1">
          <span>{t('review.breakdownText', { count: textCount })}</span>
          <span>·</span>
          <span>{t('review.breakdownOcr', { count: ocrCount })}</span>
        </div>
      </div>

      {/* Save / Network Error Banner */}
      {saveError && (
        <Banner
          variant="error"
          title={saveError.title}
          action={
            saveError.retryable
              ? {
                  label: t('review.saveErrorRetry') || 'Retry saving',
                  onClick: handleConfirmSubmit,
                }
              : undefined
          }
        >
          {saveError.message}
        </Banner>
      )}

      {/* Review Warning Banners */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          {warnings.map((warn, idx) => (
            <Banner key={idx} variant="warn" title={t('review.extractionNotice')}>
              {warn}
            </Banner>
          ))}
        </div>
      )}

      {/* Clause Cards List */}
      <div className="flex-1 space-y-3 pb-8">
        {displayedClauses.length === 0 ? (
          <div className="p-8 text-center text-xs text-mute font-mono bg-bg2/40 rounded-xl border border-line">
            {t('results.noMatches')}
          </div>
        ) : (
          displayedClauses.map((clause) => (
            <ClauseReviewCard
              key={clause.clause_id}
              clause={clause}
              editedText={corrections[clause.clause_id]}
              isActive={selectedClauseId === clause.clause_id}
              onSelect={onSelectClause}
              onSaveCorrection={handleSaveCorrection}
              onResetCorrection={handleResetCorrection}
            />
          ))
        )}
      </div>

      {/* Sticky Bottom Confirmation & Submit Action Bar */}
      <div className="sticky bottom-0 z-20 bg-paper/95 backdrop-blur-md p-4 -mx-6 -mb-6 border-t border-line shadow-[0_-8px_20px_-6px_rgba(20,48,107,0.1)] space-y-3">
        {/* Explicit confirmation checkbox */}
        <label className="flex items-start gap-3 p-3 rounded-lg border border-line bg-bg2/50 cursor-pointer select-none hover:bg-bg2/70 transition-colors">
          <input
            type="checkbox"
            checked={confirmedChecked}
            onChange={(e) => setConfirmedChecked(e.target.checked)}
            className="mt-0.5 w-4 h-4 rounded text-blue focus:ring-blue border-line"
          />
          <span className="text-xs font-semibold text-navy leading-relaxed">
            {t('review.checkboxConfirm')}
          </span>
        </label>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs font-mono text-mute">
            {Object.keys(corrections).length > 0
              ? t('review.pendingCorrections', { count: Object.keys(corrections).length })
              : t('review.allMatchExtraction')}
          </span>

          <Button
            variant="primary"
            size="md"
            disabled={!confirmedChecked || isSubmitting}
            isLoading={isSubmitting}
            onClick={handleConfirmSubmit}
            leftIcon={
              confirmedChecked ? (
                <Send className="w-4 h-4" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )
            }
          >
            {isSubmitting ? t('review.submitting') : t('review.confirmAndAnalyse')}
          </Button>
        </div>
      </div>
    </div>
  );
};
