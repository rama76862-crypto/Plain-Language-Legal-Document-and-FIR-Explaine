/**
 * DeadlinePanel Component (C-11)
 * Renders explicit dates timeline and relative time periods requiring outside information:
 * - Dates stated in document: Formatted via Intl.DateTimeFormat (en-IN, hi-IN, pa-IN), never shifted or computed.
 * - Time periods needing information: Explicitly flags "Missing: {missing_information}".
 *   Stipulates: "This document counts days from an event that is not in the file. The app does not calculate legal deadlines."
 * - Needs-review dates: Flagged for verification.
 * - Time Ribbon visualization: Visual markers for explicit dates and floating '?' markers for anchors.
 * - Persistent disclaimer: Deadlines have legal consequences.
 * - Full LegalAidDirectoryCard.
 */

import React, { useMemo } from 'react';
import {
  Calendar,
  Clock,
  AlertTriangle,
  HelpCircle,
  ShieldAlert,
  CheckCircle,
} from 'lucide-react';
import type { OutputLanguage } from '../../lib/types';
import { useResult } from './ResultContext';
import { EvidenceButton } from './EvidenceButton';
import { LegalAidDirectoryCard } from './LegalAidDirectoryCard';
import { GlassCard, Banner, MonoLabel } from '../../design/primitives';
import { useT } from '../../lib/i18n';
import { useReducedMotion } from '../../design/motion';

interface DeadlinePanelProps {
  onNavigateEvidence: (clauseId: string) => void;
}

export const DeadlinePanel: React.FC<DeadlinePanelProps> = ({ onNavigateEvidence }) => {
  const { t } = useT();
  const reduced = useReducedMotion();
  const { result, outputLanguage } = useResult();
  const deadlines = result?.deadlines || [];

  // 1. Explicit dates with resolved date
  const explicitDeadlines = useMemo(() => {
    return deadlines
      .filter((d) => d.status === 'explicit')
      .sort((a, b) => {
        if (!a.resolved_date) return 1;
        if (!b.resolved_date) return -1;
        return a.resolved_date.localeCompare(b.resolved_date);
      });
  }, [deadlines]);

  // 2. Relative time periods needing information
  const needsInfoDeadlines = useMemo(() => {
    return deadlines.filter((d) => d.status === 'needs_information');
  }, [deadlines]);

  // 3. Needs review dates
  const needsReviewDeadlines = useMemo(() => {
    return deadlines.filter((d) => d.status === 'needs_review');
  }, [deadlines]);

  // Format date helper
  const formatDate = (isoStr: string | null, lang: OutputLanguage) => {
    if (!isoStr) return '';
    try {
      const date = new Date(isoStr);
      const locale = lang === 'hi' ? 'hi-IN' : lang === 'pa' ? 'pa-IN' : 'en-IN';
      return new Intl.DateTimeFormat(locale, {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      }).format(date);
    } catch {
      return isoStr;
    }
  };

  // Human label for missing information
  const formatMissingInfo = (infoKey: string) => {
    const labels: Record<string, string> = {
      receipt_date: 'Receipt date of notice / keys',
      expiration_date: 'Contract expiration date',
      incident_date: 'Date of alleged incident',
      service_date: 'Service date of summons',
    };
    return labels[infoKey] || infoKey.replace(/_/g, ' ');
  };

  return (
    <div className="space-y-6">
      {/* Top Persistent Disclaimer */}
      <Banner variant="info">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-blue shrink-0" />
          <span>
            {t('deadlines.datesDisclaimer')}
          </span>
        </div>
      </Banner>

      {/* Summary Counts Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-lg bg-paper border border-line flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono text-mute uppercase">{t('deadlines.explicitDatesLabel')}</div>
            <div className="text-xl font-bold font-mono text-navy mt-0.5">
              {explicitDeadlines.length}
            </div>
          </div>
          <CheckCircle className="w-5 h-5 text-ok" />
        </div>

        <div className="p-3.5 rounded-lg bg-paper border border-line flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono text-mute uppercase">{t('deadlines.needsInfoLabel')}</div>
            <div className="text-xl font-bold font-mono text-navy mt-0.5">
              {needsInfoDeadlines.length}
            </div>
          </div>
          <HelpCircle className="w-5 h-5 text-blue" />
        </div>

        <div className="p-3.5 rounded-lg bg-paper border border-line flex items-center justify-between">
          <div>
            <div className="text-[11px] font-mono text-mute uppercase">{t('deadlines.needsReviewLabel')}</div>
            <div className="text-xl font-bold font-mono text-navy mt-0.5">
              {needsReviewDeadlines.length}
            </div>
          </div>
          <AlertTriangle className="w-5 h-5 text-amber-600" />
        </div>
      </div>

      {/* 3D-Tilted Time Ribbon Header */}
      {deadlines.length > 0 && (
        <div className="[perspective:1000px]">
          <div
            className={`p-4 rounded-lg bg-bg2/80 border border-line space-y-3 shadow-sm transition-transform duration-500 ${
              reduced ? '' : '[transform:rotateX(6deg)] hover:[transform:rotateX(0deg)]'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-navy uppercase flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-blue" />
                {t('deadlines.timelineRibbon')}
              </span>
              <span className="text-[10px] font-mono text-mute">{t('deadlines.ribbonSub')}</span>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto py-2">
              {explicitDeadlines.map((d) => (
                <div
                  key={d.deadline_id}
                  className="px-2.5 py-1.5 rounded bg-paper border border-line text-xs font-mono shrink-0 shadow-xs flex items-center gap-1.5 hover:shadow-md transition-shadow"
                >
                  <div className="w-2 h-2 rounded-full bg-ok animate-pulse" />
                  <span className="font-bold text-navy">
                    {d.resolved_date ? formatDate(d.resolved_date, outputLanguage) : d.display_text}
                  </span>
                  <MonoLabel>{d.clause_id}</MonoLabel>
                </div>
              ))}

              {needsInfoDeadlines.map((d) => (
                <div
                  key={d.deadline_id}
                  className={`px-2.5 py-1.5 rounded bg-blue/5 border border-blue/30 text-xs font-mono shrink-0 flex items-center gap-1.5 shadow-xs ${
                    reduced ? '' : 'animate-pulse'
                  }`}
                >
                  <div className="w-3.5 h-3.5 rounded-full border border-blue text-[10px] flex items-center justify-center font-bold text-blue">
                    ?
                  </div>
                  <span className="text-blue font-semibold">
                    {d.anchor ? d.anchor.replace(/_/g, ' ') : t('deadlines.anchorEvent')}
                  </span>
                  <MonoLabel>{d.clause_id}</MonoLabel>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {deadlines.length === 0 && (
        <GlassCard className="p-8 text-center space-y-2">
          <Calendar className="w-8 h-8 text-mute mx-auto" />
          <h4 className="text-sm font-bold text-navy">
            {t('deadlines.emptyState')}
          </h4>
          <p className="text-xs text-mute max-w-sm mx-auto">
            {t('deadlines.emptyStateSub')}
          </p>
        </GlassCard>
      )}

      {/* SECTION A: Dates Stated in Document (Explicit) */}
      {explicitDeadlines.length > 0 && (
        <div className="space-y-4">
          <div className="pb-1 border-b border-line">
            <h3 className="text-sm font-bold text-navy flex items-center gap-2">
              <Calendar className="w-4 h-4 text-ok" />
              {t('deadlines.statedDatesTitle')} ({explicitDeadlines.length})
            </h3>
            <p className="text-xs text-mute">
              {t('deadlines.statedDatesSub')}
            </p>
          </div>

          <div className="space-y-3 relative pl-4 border-l-2 border-ok/40">
            {explicitDeadlines.map((d) => (
              <GlassCard key={d.deadline_id} className="p-4 space-y-2 relative">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold font-mono text-navy bg-ok/10 text-ok px-2 py-0.5 rounded">
                      {d.resolved_date ? formatDate(d.resolved_date, outputLanguage) : d.display_text}
                    </span>
                    <MonoLabel>{d.clause_id}</MonoLabel>
                  </div>

                  <EvidenceButton
                    clauseId={d.clause_id}
                    onNavigateEvidence={onNavigateEvidence}
                  />
                </div>

                <div className="text-xs text-navy font-semibold">{d.display_text}</div>

                <blockquote className="text-xs font-serif italic text-mute border-l-2 border-line pl-2">
                  "{d.source_quote}"
                </blockquote>
              </GlassCard>
            ))}
          </div>
        </div>
      )}

      {/* SECTION B: Time Periods Needing More Information */}
      {needsInfoDeadlines.length > 0 && (
        <div className="space-y-4">
          <div className="pb-1 border-b border-line">
            <h3 className="text-sm font-bold text-navy flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-blue" />
              {t('deadlines.relativePeriodsTitle')} ({needsInfoDeadlines.length})
            </h3>
            <p className="text-xs text-mute">
              {t('deadlines.relativePeriodNote')}
            </p>
          </div>

          <div className="space-y-3">
            {needsInfoDeadlines.map((d) => (
              <GlassCard
                key={d.deadline_id}
                className="p-4 space-y-3 border-blue/30 bg-blue/5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-navy">{d.display_text}</span>
                    <MonoLabel>{d.clause_id}</MonoLabel>
                  </div>

                  <EvidenceButton
                    clauseId={d.clause_id}
                    onNavigateEvidence={onNavigateEvidence}
                  />
                </div>

                <blockquote className="text-xs font-serif italic text-navy/90 border-l-2 border-blue pl-2 bg-paper/60 p-1.5 rounded-r">
                  "{d.source_quote}"
                </blockquote>

                {/* Missing Information Callout Row */}
                <div className="p-2.5 rounded bg-paper border border-line text-xs space-y-1">
                  <div className="text-[11px] font-mono uppercase text-mute font-semibold">
                    {t('deadlines.startingAnchor')}
                  </div>
                  <div className="text-navy font-mono font-medium">
                    {t('deadlines.startsFrom')} <strong>{d.anchor ? d.anchor.replace(/_/g, ' ') : 'unspecified event'}</strong>
                  </div>

                  {d.missing_information && d.missing_information.length > 0 && (
                    <div className="pt-1 border-t border-line/60 text-amber-800 flex items-center gap-1 font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>
                        {t('deadlines.missingInfoPrefix')} {d.missing_information.map(formatMissingInfo).join(', ')}
                      </span>
                    </div>
                  )}
                </div>
              </GlassCard>
            ))}
          </div>
        </div>
      )}

      {/* SECTION C: Needs Review Dates */}
      {needsReviewDeadlines.length > 0 && (
        <div className="space-y-3">
          <div className="pb-1 border-b border-line">
            <h3 className="text-sm font-bold text-amber-900 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
              {t('deadlines.needsReviewTitle', { count: needsReviewDeadlines.length })}
            </h3>
          </div>

          <div className="space-y-2">
            {needsReviewDeadlines.map((d) => (
              <GlassCard key={d.deadline_id} className="p-4 space-y-2 border-amber-500/30">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-amber-900">{d.display_text}</span>
                  <EvidenceButton
                    clauseId={d.clause_id}
                    onNavigateEvidence={onNavigateEvidence}
                  />
                </div>
                <p className="text-xs text-amber-800">
                  {t('deadlines.needsReviewSub')}
                </p>
                <blockquote className="text-xs font-serif italic text-mute border-l-2 border-line pl-2">
                  "{d.source_quote}"
                </blockquote>
              </GlassCard>
            ))}
          </div>
        </div>
      )}

      {/* Full Legal Aid Directory Card */}
      <div className="pt-4 border-t border-line">
        <LegalAidDirectoryCard legalAid={result?.legal_aid} variant="full" />
      </div>
    </div>
  );
};
export default DeadlinePanel;
