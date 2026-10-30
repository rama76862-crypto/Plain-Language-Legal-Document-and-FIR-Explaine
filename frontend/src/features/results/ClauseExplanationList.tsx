/**
 * ClauseExplanationList Component (C-09)
 * Renders every clause in document order with comprehensive explanations:
 * - Search bar across original text and explanations
 * - Filter chips: All, Potential concerns, Needs review, Has deadline
 * - Keyboard navigation (j/k to traverse, Enter to focus evidence)
 * - Show mode toggle: Card view vs Compact table view
 * - FIR pinned banner (presumption of innocence) and Notice pinned banner
 * - Unanalysed clauses fallback card with "Show in source"
 */

import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  Search,
  SlidersHorizontal,
  Table,
  LayoutGrid,
  AlertTriangle,
  Scale,
  FileCheck,
  Eye,
  CheckCircle,
} from 'lucide-react';
import type { Clause } from '../../lib/types';
import { useResult } from './ResultContext';
import { useSession } from '../../lib/session';
import { EvidenceCard } from './EvidenceCard';
import { Banner, MonoLabel } from '../../design/primitives';
import { useT } from '../../lib/i18n';

interface ClauseExplanationListProps {
  onNavigateEvidence: (clauseId: string) => void;
  clauses?: Clause[];
}

type FilterType = 'all' | 'attention' | 'needs_review' | 'deadline';

export const ClauseExplanationList: React.FC<ClauseExplanationListProps> = ({
  onNavigateEvidence,
  clauses: externalClauses,
}) => {
  const { t } = useT();
  const { result, outputLanguage } = useResult();
  const { selectedClauseId } = useSession();

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeFilter, setActiveFilter] = useState<FilterType>('all');
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card');
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);

  const containerRef = useRef<HTMLDivElement | null>(null);

  const items = result?.items || [];
  const deadlines = result?.deadlines || [];
  const references = result?.references || [];
  const documentType = result?.document_type || 'agreement';

  // Set of clause IDs that have deadlines
  const deadlineClauseIds = useMemo(() => {
    return new Set(deadlines.map((d) => d.clause_id));
  }, [deadlines]);

  // Filtered and searched items
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      // 1. Filter match
      if (activeFilter === 'attention') {
        if (item.kind !== 'attention' && item.kind !== 'allegation' && item.kind !== 'notice_action') {
          return false;
        }
      } else if (activeFilter === 'needs_review') {
        if (item.review_status !== 'needs_review') {
          return false;
        }
      } else if (activeFilter === 'deadline') {
        if (!deadlineClauseIds.has(item.clause_id)) {
          return false;
        }
      }

      // 2. Search query match
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const inExplanation = item.explanation.toLowerCase().includes(q);
      const inClauseId = item.clause_id.toLowerCase().includes(q);
      const inQuote = item.evidence?.some((e) => e.quote.toLowerCase().includes(q));
      return inExplanation || inClauseId || inQuote;
    });
  }, [items, activeFilter, searchQuery, deadlineClauseIds]);

  // Keyboard navigation (j/k, Enter)
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;

      if (e.key === 'j') {
        setFocusedIndex((prev) => Math.min(prev + 1, filteredItems.length - 1));
      } else if (e.key === 'k') {
        setFocusedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter' && focusedIndex >= 0 && focusedIndex < filteredItems.length) {
        const targetItem = filteredItems[focusedIndex];
        if (targetItem) {
          onNavigateEvidence(targetItem.clause_id);
        }
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [filteredItems, focusedIndex, onNavigateEvidence]);

  // Scroll to active clause if selected from source viewer
  useEffect(() => {
    if (selectedClauseId && containerRef.current) {
      const el = containerRef.current.querySelector(`[data-clause-id="${selectedClauseId}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [selectedClauseId]);

  // Counts for filter badges
  const attentionCount = items.filter(
    (i) => i.kind === 'attention' || i.kind === 'allegation' || i.kind === 'notice_action'
  ).length;
  const needsReviewCount = items.filter((i) => i.review_status === 'needs_review').length;
  const deadlineCount = items.filter((i) => deadlineClauseIds.has(i.clause_id)).length;

  return (
    <div ref={containerRef} className="space-y-5">
      {/* Pinned Document-Type Legal Disclaimers */}
      {documentType === 'fir' && (
        <Banner variant="info">
          <div className="flex items-center gap-2">
            <Scale className="w-4 h-4 text-blue shrink-0" />
            <span className="font-semibold">
              {t('disclaimers.fir')}
            </span>
          </div>
        </Banner>
      )}

      {documentType === 'notice' && (
        <Banner variant="info">
          <div className="flex items-center gap-2">
            <FileCheck className="w-4 h-4 text-blue shrink-0" />
            <span>
              {t('disclaimers.notice')}
            </span>
          </div>
        </Banner>
      )}

      {/* Controls Bar: Search + Filters + View Mode */}
      <div className="p-4 rounded-lg bg-paper border border-line space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Search Box */}
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-mute" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('results.searchPlaceholder')}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-md border border-line bg-bg focus:outline-hidden focus:ring-2 focus:ring-blue"
            />
          </div>

          {/* View Mode Toggle */}
          <div className="flex items-center gap-1 p-1 bg-bg2 rounded border border-line text-xs">
            <button
              type="button"
              onClick={() => setViewMode('card')}
              className={`p-1.5 rounded transition-colors ${
                viewMode === 'card' ? 'bg-paper text-navy shadow-xs font-bold' : 'text-mute'
              }`}
              title={t('results.cardView')}
              aria-label={t('results.cardView')}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded transition-colors ${
                viewMode === 'table' ? 'bg-paper text-navy shadow-xs font-bold' : 'text-mute'
              }`}
              title={t('results.tableView')}
              aria-label={t('results.tableView')}
            >
              <Table className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Filter Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-line/60">
          <span className="text-[11px] font-mono text-mute flex items-center gap-1 mr-1">
            <SlidersHorizontal className="w-3 h-3" />
            {t('results.filterLabel')}
          </span>

          <button
            type="button"
            onClick={() => setActiveFilter('all')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
              activeFilter === 'all'
                ? 'bg-navy text-white font-semibold'
                : 'bg-bg2 text-mute hover:text-navy'
            }`}
          >
            {t('results.filterAll', { count: items.length })}
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter('attention')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors flex items-center gap-1 ${
              activeFilter === 'attention'
                ? 'bg-amber-600 text-white font-semibold'
                : 'bg-amber-500/10 text-amber-800 hover:bg-amber-500/20'
            }`}
          >
            <span>{t('results.filterConcerns')}</span>
            <span className="text-[10px] font-mono font-bold">({attentionCount})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter('needs_review')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors flex items-center gap-1 ${
              activeFilter === 'needs_review'
                ? 'bg-amber-700 text-white font-semibold'
                : 'bg-bg2 text-mute hover:text-navy'
            }`}
          >
            <span>{t('results.filterNeedsReview')}</span>
            <span className="text-[10px] font-mono">({needsReviewCount})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveFilter('deadline')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors flex items-center gap-1 ${
              activeFilter === 'deadline'
                ? 'bg-blue text-white font-semibold'
                : 'bg-bg2 text-mute hover:text-navy'
            }`}
          >
            <span>{t('results.filterDeadline')}</span>
            <span className="text-[10px] font-mono">({deadlineCount})</span>
          </button>
        </div>
      </div>

      {/* Empty Filter State */}
      {filteredItems.length === 0 && (
        <div className="p-8 text-center rounded-lg border border-dashed border-line bg-paper/60 space-y-2">
          <p className="text-xs text-mute">{t('results.noMatches')}</p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery('');
              setActiveFilter('all');
            }}
            className="text-xs text-blue hover:underline font-semibold"
          >
            {t('results.resetFilters')}
          </button>
        </div>
      )}

      {/* View Mode: Card View */}
      {viewMode === 'card' && filteredItems.length > 0 && (
        <div className="space-y-4">
          {filteredItems.map((item, idx) => {
            const clause = externalClauses?.find((c) => c.clause_id === item.clause_id);
            const isFocused = focusedIndex === idx;
            const isSelected = selectedClauseId === item.clause_id;

            return (
              <EvidenceCard
                key={item.item_id}
                item={item}
                clause={clause}
                outputLanguage={outputLanguage}
                references={references}
                onNavigateEvidence={onNavigateEvidence}
                isActive={isSelected || isFocused}
              />
            );
          })}
        </div>
      )}

      {/* View Mode: Table View */}
      {viewMode === 'table' && filteredItems.length > 0 && (
        <div className="rounded-lg border border-line bg-paper overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-bg2/80 border-b border-line text-mute font-mono text-[11px] uppercase">
                  <th className="p-3 w-16">{t('results.tableId')}</th>
                  <th className="p-3 w-28">{t('results.tableType')}</th>
                  <th className="p-3">{t('results.tableExplanation')}</th>
                  <th className="p-3 w-28">{t('results.tableStatus')}</th>
                  <th className="p-3 w-24 text-right">{t('results.tableEvidence')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/60">
                {filteredItems.map((item) => (
                  <tr
                    key={item.item_id}
                    className={`hover:bg-bg2/40 transition-colors ${
                      selectedClauseId === item.clause_id ? 'bg-blue/5' : ''
                    }`}
                  >
                    <td className="p-3 font-mono font-bold text-navy">{item.clause_id}</td>
                    <td className="p-3 font-mono text-[11px]">
                      {item.kind === 'attention' ? (
                        <span className="text-amber-800 font-semibold uppercase">{t('results.badgeConcern')}</span>
                      ) : item.kind === 'allegation' ? (
                        <span className="text-blue font-semibold uppercase">{t('results.badgeAllegation')}</span>
                      ) : item.kind === 'notice_action' ? (
                        <span className="text-blue font-semibold uppercase">{t('results.badgeAction')}</span>
                      ) : (
                        <span className="text-mute uppercase">{t('results.badgeStandard')}</span>
                      )}
                    </td>
                    <td className="p-3 text-navy font-medium leading-relaxed max-w-md">
                      {item.explanation}
                    </td>
                    <td className="p-3">
                      {item.review_status === 'needs_review' ? (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono text-amber-700 bg-amber-500/10 px-1.5 py-0.5 rounded">
                          <AlertTriangle className="w-3 h-3" />
                          {t('results.badgeVerify')}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[10px] font-mono text-ok bg-ok/10 px-1.5 py-0.5 rounded">
                          <CheckCircle className="w-3 h-3" />
                          {t('results.badgeVerified')}
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-right">
                      <button
                        type="button"
                        onClick={() => onNavigateEvidence(item.clause_id)}
                        className="inline-flex items-center gap-1 text-xs text-blue hover:underline font-mono"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        <span>{t('results.badgeView')}</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Unanalysed Clauses (if any exist in external clauses but not in items) */}
      {externalClauses &&
        externalClauses
          .filter((c) => !items.some((i) => i.clause_id === c.clause_id))
          .map((c) => (
            <div
              key={c.clause_id}
              className="p-4 rounded-lg border border-dashed border-line bg-bg2/40 flex items-center justify-between text-xs"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <MonoLabel>{c.clause_id}</MonoLabel>
                  <span className="text-mute font-medium">{t('results.unanalysedNotice')}</span>
                </div>
                <p className="text-mute line-clamp-1">{c.reviewed_text}</p>
              </div>
              <button
                type="button"
                onClick={() => onNavigateEvidence(c.clause_id)}
                className="text-xs font-semibold text-blue hover:underline shrink-0 font-mono"
              >
                {t('review.showInSource')} &rarr;
              </button>
            </div>
          ))}
    </div>
  );
};
export default ClauseExplanationList;
