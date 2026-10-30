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

  const textCount = clauses.filter((c) => c.extraction_method === 'text').length;
  const ocrCount = clauses.filter((c) => c.extraction_method === 'ocr').length;
  const reviewRequiredCount = clauses.filter((c) => c.review_required).length;

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

        <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-mute pt-1">
          <span>{t('review.breakdownText', { count: textCount })}</span>
          <span>·</span>
          <span>{t('review.breakdownOcr', { count: ocrCount })}</span>
          {reviewRequiredCount > 0 && (
            <>
              <span>·</span>
              <span className="text-caution-ink font-bold flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-caution" />
                {t('review.reviewRequiredCount', { count: reviewRequiredCount })}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Review Warning Banners */}
      {warnings.length > 0 && (
        <div className="space-y-2">
          {warnings.map((warn, idx) => (
            <Banner key={idx} variant="warn" title="Extraction Notice">
              {warn}
            </Banner>
          ))}
        </div>
      )}

      {/* Clause Cards List */}
      <div className="space-y-3">
        {clauses.map((clause) => (
          <ClauseReviewCard
            key={clause.clause_id}
            clause={clause}
            editedText={corrections[clause.clause_id]}
            isActive={selectedClauseId === clause.clause_id}
            onSelect={onSelectClause}
            onSaveCorrection={handleSaveCorrection}
            onResetCorrection={handleResetCorrection}
          />
        ))}
      </div>

      {/* Confirmation & Submit Action Bar */}
      <div className="pt-6 border-t border-line space-y-4">
        {/* Explicit confirmation checkbox */}
        <label className="flex items-start gap-3 p-3.5 rounded-lg border border-line bg-bg2/40 cursor-pointer select-none">
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
              ? `${Object.keys(corrections).length} corrections pending submittal`
              : 'All clauses match extraction'}
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
