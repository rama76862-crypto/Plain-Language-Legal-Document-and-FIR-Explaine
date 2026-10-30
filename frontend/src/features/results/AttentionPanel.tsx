/**
 * AttentionPanel Component (C-10)
 * Highlights potential legal concerns and attention cues:
 * - Factual: "These are cues to read carefully, not legal conclusions."
 * - Category filter chips with exact item counts
 * - Exact source quotes in blockquotes with left rule
 * - EvidenceButton navigation to source viewer
 * - Exact empty state: "No configured attention cues detected; review all clauses."
 * - Zero safety meters, risk percentages, or traffic-light scores.
 */

import React, { useState, useMemo } from 'react';
import { ShieldAlert, Scale, FileCheck, Info } from 'lucide-react';
import type { Clause } from '../../lib/types';
import { useResult } from './ResultContext';
import { EvidenceButton } from './EvidenceButton';
import { GlassCard, Button, Banner, MonoLabel } from '../../design/primitives';
import { useT } from '../../lib/i18n';

interface AttentionPanelProps {
  onNavigateEvidence: (clauseId: string) => void;
  onGoToClauses: () => void;
  clauses?: Clause[];
}

export const AttentionPanel: React.FC<AttentionPanelProps> = ({
  onNavigateEvidence,
  onGoToClauses,
  clauses = [],
}) => {
  const { t } = useT();
  const { result } = useResult();
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const items = result?.items || [];
  const documentType = result?.document_type || 'agreement';

  // Filter items matching attention cues
  const attentionItems = useMemo(() => {
    return items.filter((i) => {
      if (documentType === 'fir') {
        return i.kind === 'allegation';
      }
      if (documentType === 'notice') {
        return i.kind === 'notice_action';
      }
      return i.kind === 'attention';
    });
  }, [items, documentType]);

  // Unique categories
  const categories = useMemo(() => {
    const cats = new Map<string, number>();
    attentionItems.forEach((item) => {
      const cat = item.category || 'general';
      cats.set(cat, (cats.get(cat) || 0) + 1);
    });
    return Array.from(cats.entries());
  }, [attentionItems]);

  // Items filtered by category
  const displayedItems = useMemo(() => {
    if (selectedCategory === 'all') return attentionItems;
    return attentionItems.filter((i) => (i.category || 'general') === selectedCategory);
  }, [attentionItems, selectedCategory]);

  return (
    <div className="space-y-5">
      {/* Pinned Disclaimer for Document Type */}
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

      {/* Header */}
      <div className="pb-3 border-b border-line space-y-1">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-600" />
          <h3 className="text-sm font-bold text-navy">
            {documentType === 'fir'
              ? t('attention.firHeader')
              : documentType === 'notice'
              ? t('attention.noticeHeader')
              : t('attention.title')}
          </h3>
        </div>
        <p className="text-xs text-mute">
          {t('attention.sub')}
        </p>
      </div>

      {/* Category Filter Chips (if more than 1 category) */}
      {categories.length > 1 && (
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setSelectedCategory('all')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
              selectedCategory === 'all'
                ? 'bg-navy text-white font-semibold'
                : 'bg-bg2 text-mute hover:text-navy'
            }`}
          >
            {t('attention.allCues', { count: attentionItems.length })}
          </button>
          {categories.map(([cat, count]) => (
            <button
              key={cat}
              type="button"
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 text-xs rounded font-medium transition-colors flex items-center gap-1.5 ${
                selectedCategory === cat
                  ? 'bg-amber-600 text-white font-semibold'
                  : 'bg-amber-500/10 text-amber-800 hover:bg-amber-500/20'
              }`}
            >
              <span>{cat.replace(/_/g, ' ')}</span>
              <span className="text-[10px] font-mono font-bold">({count})</span>
            </button>
          ))}
        </div>
      )}

      {/* Empty State: EXACT COPY REQUIRED */}
      {displayedItems.length === 0 && (
        <GlassCard className="p-8 text-center space-y-4">
          <div className="w-10 h-10 rounded-full bg-ok/10 text-ok flex items-center justify-center mx-auto">
            <Info className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-navy">
              {t('attention.emptyState')}
            </h4>
            <p className="text-xs text-mute max-w-sm mx-auto">
              {t('attention.emptyStateSub')}
            </p>
          </div>
          <Button variant="secondary" size="sm" onClick={onGoToClauses}>
            {t('attention.goToClauses')}
          </Button>
        </GlassCard>
      )}

      {/* Attention Cards List */}
      {displayedItems.length > 0 && (
        <div className="space-y-4">
          {displayedItems.map((item) => {
            const clause = clauses.find((c) => c.clause_id === item.clause_id);
            const pageNum = clause?.source_ref.page_number;
            const paraIdx = clause?.source_ref.paragraph_index;
            const exactQuote = item.evidence?.[0]?.quote || '';

            return (
              <GlassCard
                key={item.item_id}
                className="p-5 space-y-3.5 border-amber-500/30 bg-amber-500/5 hover:border-amber-500/50 transition-all"
              >
                {/* Card Header: Category & Location */}
                <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-amber-500/20">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold uppercase bg-amber-500/20 text-amber-900">
                      {t('attention.concernPrefix')} {item.category?.replace(/_/g, ' ') || 'Notice Cue'}
                    </span>
                    <MonoLabel>{item.clause_id}</MonoLabel>
                    {pageNum && (
                      <span className="text-xs font-mono text-mute">p.{pageNum}</span>
                    )}
                    {paraIdx && (
                      <span className="text-xs font-mono text-mute">¶ {paraIdx}</span>
                    )}
                  </div>

                  <EvidenceButton
                    clauseId={item.clause_id}
                    pageNumber={pageNum}
                    paragraphIndex={paraIdx}
                    onNavigateEvidence={onNavigateEvidence}
                  />
                </div>

                {/* Why it matters (Explanation) */}
                <div className="space-y-1">
                  <span className="text-[11px] font-mono uppercase text-amber-900/80 font-bold">
                    {t('attention.whyItMatters')}
                  </span>
                  <p className="text-xs text-navy font-medium leading-[1.7] whitespace-pre-line">
                    {item.explanation}
                  </p>
                </div>

                {/* Exact Quote */}
                {exactQuote && (
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono uppercase text-mute">
                      {t('attention.exactQuote')}
                    </span>
                    <blockquote className="border-l-2 border-amber-600 pl-3 py-1 font-serif text-xs italic text-navy bg-paper/60 rounded-r">
                      "{exactQuote}"
                    </blockquote>
                  </div>
                )}

                {/* Limitations */}
                {item.limitations && item.limitations.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {item.limitations.map((lim, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-800"
                      >
                        {lim}
                      </span>
                    ))}
                  </div>
                )}

                {/* Footer disclaimer line */}
                <div className="pt-2 border-t border-amber-500/15 text-[10px] font-mono text-mute flex items-center justify-between">
                  <span>{t('disclaimers.footer')}</span>
                  <span>{t('attention.readFullClause')}</span>
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}
    </div>
  );
};
export default AttentionPanel;
