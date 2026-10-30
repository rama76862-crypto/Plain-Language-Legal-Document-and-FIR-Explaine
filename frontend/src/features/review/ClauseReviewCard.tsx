/**
 * ClauseReviewCard Component
 * Displays individual clause with source location, extraction method,
 * inline editing textarea, diff viewer, and bidirectional source scroll link.
 */

import React, { useState, useRef, useEffect } from 'react';
import type { Clause } from '../../lib/types';
import { Button, MonoLabel, StatusPill } from '../../design/primitives';
import { useT } from '../../lib/i18n';
import { Edit3, RotateCcw, Eye, Check, AlertCircle } from 'lucide-react';

interface ClauseReviewCardProps {
  clause: Clause;
  editedText?: string;
  isActive?: boolean;
  onSelect: (clauseId: string) => void;
  onSaveCorrection: (clauseId: string, newText: string) => void;
  onResetCorrection: (clauseId: string) => void;
}

export const ClauseReviewCard: React.FC<ClauseReviewCardProps> = ({
  clause,
  editedText,
  isActive = false,
  onSelect,
  onSaveCorrection,
  onResetCorrection,
}) => {
  const { t } = useT();
  const currentText = editedText !== undefined ? editedText : clause.reviewed_text;
  const isModified = currentText !== clause.source_text;

  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(currentText);
  const [showDiff, setShowDiff] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    setEditText(currentText);
  }, [currentText]);

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [isEditing]);

  const handleSave = () => {
    const trimmed = editText.trim();
    if (trimmed.length === 0) {
      setErrorMsg(t('review.emptyClauseError'));
      return;
    }
    if (trimmed.length > 10000) {
      setErrorMsg(t('review.maxLimitError'));
      return;
    }

    setErrorMsg(null);
    onSaveCorrection(clause.clause_id, trimmed);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditText(currentText);
    setErrorMsg(null);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    }
  };

  // Location representation: PDF has page_number; DOCX strictly paragraph_index
  const locationLabel = clause.source_ref.page_number
    ? `p.${clause.source_ref.page_number}`
    : clause.source_ref.paragraph_index
    ? `¶ ${clause.source_ref.paragraph_index}`
    : '§';

  return (
    <article
      id={`review-clause-${clause.clause_id}`}
      data-evidence-source={isActive ? 'active' : undefined}
      className={`p-4 rounded-lg border transition-all ${
        isActive
          ? 'bg-blue/5 border-blue shadow-sm ring-2 ring-cyan/40'
          : 'bg-paper border-line hover:border-blue/30'
      }`}
    >
      {/* Top Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2 mb-3 border-b border-line/60">
        <div className="flex items-center gap-2">
          {/* Clause ID Chip */}
          <span className="px-2 py-0.5 rounded bg-navy text-white font-mono text-xs font-bold">
            {clause.clause_id}
          </span>
          {/* Location Chip */}
          <span className="px-2 py-0.5 rounded bg-bg2 text-navy font-mono text-xs font-semibold">
            {locationLabel}
          </span>
          {/* Extraction Method */}
          <span className="font-mono text-[10px] text-mute uppercase px-1.5 py-0.5 rounded bg-line/60">
            {clause.extraction_method}
          </span>
          {/* Edited Badge */}
          {isModified && (
            <span className="px-1.5 py-0.5 rounded bg-cyan/15 text-cyan-ink font-mono text-[10px] font-bold">
              {t('review.editedBadge')}
            </span>
          )}
        </div>

        {/* Status badges */}
        <div className="flex items-center gap-2">
          {clause.review_required && !isModified && (
            <StatusPill variant="caution">
              {t('review.reviewRequiredCount', { count: 1 })}
            </StatusPill>
          )}
        </div>
      </div>

      {/* Clause Body Text / Edit Mode */}
      {isEditing ? (
        <div className="space-y-3">
          <textarea
            ref={textareaRef}
            value={editText}
            onChange={(e) => {
              setEditText(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${e.target.scrollHeight}px`;
            }}
            onKeyDown={handleKeyDown}
            className="w-full p-3 rounded-md border border-blue bg-paper text-ink font-sans text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue resize-none min-h-[90px]"
            aria-label={`Edit text for clause ${clause.clause_id}`}
          />

          {errorMsg && (
            <div className="flex items-center gap-1.5 text-xs text-concern font-semibold">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <span className="font-mono text-xs text-mute">
              {t('review.charCount', { count: editText.length })} · <MonoLabel>{t('review.ctrlEnterToSave')}</MonoLabel>
            </span>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={handleCancel}>
                {t('review.cancelEdit')}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSave}
                leftIcon={<Check className="w-3.5 h-3.5" />}
              >
                {t('review.saveEdit')}
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-ink text-sm leading-relaxed whitespace-pre-wrap selection:bg-blue/20">
            {currentText}
          </p>

          {/* Diff View Toggle if edited */}
          {isModified && showDiff && (
            <div className="p-3 rounded bg-bg2/80 border border-line text-xs space-y-1 font-mono">
              <div className="text-mute font-bold">{t('review.originalExtraction')}</div>
              <p className="text-mute line-through">{clause.source_text}</p>
            </div>
          )}

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-line/40 text-xs">
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<Eye className="w-3.5 h-3.5 text-blue" />}
                onClick={() => onSelect(clause.clause_id)}
              >
                {t('review.showInSource')}
              </Button>
              {isModified && (
                <button
                  type="button"
                  onClick={() => setShowDiff(!showDiff)}
                  className="text-mute hover:text-navy underline text-xs font-mono ml-2"
                >
                  {showDiff ? t('review.hideDiff') : t('review.showOriginal')}
                </button>
              )}
            </div>

            <div className="flex items-center gap-2">
              {isModified && (
                <Button
                  variant="ghost"
                  size="sm"
                  leftIcon={<RotateCcw className="w-3.5 h-3.5 text-mute" />}
                  onClick={() => onResetCorrection(clause.clause_id)}
                >
                  {t('review.resetClause')}
                </Button>
              )}
              <Button
                variant="secondary"
                size="sm"
                leftIcon={<Edit3 className="w-3.5 h-3.5 text-navy" />}
                onClick={() => setIsEditing(true)}
              >
                {t('review.editClause')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </article>
  );
};
