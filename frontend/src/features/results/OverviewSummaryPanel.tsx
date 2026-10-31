/**
 * OverviewSummaryPanel Component (C-08)
 * Presents a factual, objective summary of the analysis:
 * - Coverage ring and count of analysed clauses
 * - Document synopsis & item breakdowns
 * - Translation-assisted working copy notice when relevant
 * - Model provenance expander
 * - Persistent disclaimer card & Legal aid mini-card
 * - STRICT RULE: Never presents safety scores, risk percentages, or verdicts.
 */

import React, { useState } from 'react';
import {
  FileText,
  AlertTriangle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Cpu,
  ShieldCheck,
  Phone,
} from 'lucide-react';
import { useResult } from './ResultContext';
import { useT } from '../../lib/i18n';
import { CoverageRing } from '../../design/scenes/CoverageRing';
import { GlassCard, Button, Banner, MonoLabel } from '../../design/primitives';

interface OverviewSummaryPanelProps {
  onNavigateEvidence: (clauseId: string) => void;
  onGoToClauses: () => void;
  filename?: string;
}

export const OverviewSummaryPanel: React.FC<OverviewSummaryPanelProps> = ({
  onNavigateEvidence,
  onGoToClauses,
  filename = 'Document',
}) => {
  const { t } = useT();
  const { result, actionPack, verificationResult, setActiveTab } = useResult();
  const [showTechDetails, setShowTechDetails] = useState<boolean>(false);

  if (!result) return null;

  const analysed = result.coverage?.analysed ?? 0;
  const total = result.coverage?.total ?? 0;
  const isPartial = analysed < total;

  // Breakdowns
  const explanationCount = result.items.filter((i) => i.kind === 'explanation').length;
  const attentionCount = result.items.filter((i) => i.kind === 'attention').length;
  const allegationCount = result.items.filter((i) => i.kind === 'allegation').length;
  const noticeActionCount = result.items.filter((i) => i.kind === 'notice_action').length;
  const explicitDeadlines = result.deadlines.filter((d) => d.status === 'explicit').length;
  const unresolvedDeadlines = result.deadlines.filter((d) => d.status === 'needs_information').length;

  // Skipped or needs-review items
  const needsReviewItems = result.items.filter((i) => i.review_status === 'needs_review');

  // Translation-assisted check
  const isTranslationAssisted =
    result.input_language !== 'en' ||
    result.warnings.some((w) => w.toLowerCase().includes('translation')) ||
    result.items.some((i) =>
      i.limitations?.some((l) => l.toLowerCase().includes('translation'))
    );

  return (
    <div className="space-y-6">
      {/* Partial Analysis Warning */}
      {isPartial && (
        <Banner variant="warn" title={t('overview.partialTitle')}>
          {t('overview.partialBody', { analysed, total })}
        </Banner>
      )}

      {/* Translation-Assisted Notice */}
      {isTranslationAssisted && (
        <Banner variant="info" title={t('overview.translationAssistedTitle')}>
          {t('overview.translationAssistedBody')}
        </Banner>
      )}

      {/* Top Coverage & Synopsis Card */}
      <GlassCard className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
          {/* Coverage Ring */}
          <div className="md:col-span-4 flex flex-col items-center justify-center p-2 border-b md:border-b-0 md:border-r border-line pb-6 md:pb-0">
            <CoverageRing analysed={analysed} total={total} />
            <div className="mt-3 text-center">
              <div className="text-sm font-semibold text-navy">
                {t('overview.analysedCount', { analysed, total })}
              </div>
              <p className="text-xs text-mute mt-0.5">
                {isPartial
                  ? t('results.partialNotice')
                  : t('overview.coverageTitle')}
              </p>
            </div>
          </div>

          {/* Synopsis Metadata */}
          <div className="md:col-span-8 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue" />
                <h3 className="text-base font-bold text-navy truncate max-w-xs">{filename}</h3>
              </div>
              <div className="flex items-center gap-2">
                <MonoLabel>{t('review.revisionLabel', { rev: result.document_revision })}</MonoLabel>
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold uppercase rounded bg-bg2 text-navy border border-line">
                  {result.document_type}
                </span>
              </div>
            </div>

            {/* Language Flow */}
            <div className="flex items-center gap-2 text-xs text-mute">
              <span>{t('overview.inputLabel')} <strong className="text-navy uppercase">{result.input_language}</strong></span>
              <span>&rarr;</span>
              <span>{t('overview.explainedInLabel')} <strong className="text-blue uppercase">{result.output_language}</strong></span>
            </div>

            {/* Metrics Breakdown Matrix */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
              <div className="p-2.5 rounded bg-bg2/60 border border-line">
                <div className="text-[11px] font-mono text-mute uppercase truncate">
                  {t('overview.explanationsMetric')}
                </div>
                <div className="text-xl font-bold font-mono text-navy mt-1">
                  {explanationCount}
                </div>
              </div>

              {result.document_type === 'fir' ? (
                <div className="p-2.5 rounded bg-blue/5 border border-blue/20">
                  <div className="text-[11px] font-mono text-blue uppercase truncate">
                    {t('overview.allegationsMetric')}
                  </div>
                  <div className="text-xl font-bold font-mono text-blue mt-1">
                    {allegationCount}
                  </div>
                </div>
              ) : result.document_type === 'notice' ? (
                <div className="p-2.5 rounded bg-blue/5 border border-blue/20">
                  <div className="text-[11px] font-mono text-blue uppercase truncate">
                    {t('overview.actionsMetric')}
                  </div>
                  <div className="text-xl font-bold font-mono text-blue mt-1">
                    {noticeActionCount}
                  </div>
                </div>
              ) : (
                <div className="p-2.5 rounded bg-amber-500/10 border border-amber-500/20">
                  <div className="text-[11px] font-mono text-amber-700 uppercase truncate">
                    {t('overview.attentionMetric')}
                  </div>
                  <div className="text-xl font-bold font-mono text-amber-800 mt-1">
                    {attentionCount}
                  </div>
                </div>
              )}

              <div className="p-2.5 rounded bg-bg2/60 border border-line">
                <div className="text-[11px] font-mono text-mute uppercase truncate">
                  {t('overview.explicitDatesMetric')}
                </div>
                <div className="text-xl font-bold font-mono text-navy mt-1">
                  {explicitDeadlines}
                </div>
              </div>

              <div className="p-2.5 rounded bg-bg2/60 border border-line">
                <div className="text-[11px] font-mono text-mute uppercase truncate">
                  {t('overview.unresolvedDatesMetric')}
                </div>
                <div className="text-xl font-bold font-mono text-navy mt-1">
                  {unresolvedDeadlines}
                </div>
              </div>

              {/* Obligations Tile */}
              <button
                type="button"
                onClick={() => setActiveTab('actionPack')}
                className="p-2.5 rounded bg-bg2/60 border border-line hover:border-blue text-left transition-colors cursor-pointer group"
              >
                <div className="text-[11px] font-mono text-mute group-hover:text-blue uppercase truncate">
                  {t('overview.obligations')}
                </div>
                <div className="text-xl font-bold font-mono text-navy mt-1">
                  {actionPack?.checklist ? actionPack.checklist.length : '—'}
                </div>
              </button>

              {/* Source Verification Tile */}
              <button
                type="button"
                onClick={() => setActiveTab('verify')}
                className="p-2.5 rounded bg-bg2/60 border border-line hover:border-blue text-left transition-colors cursor-pointer group"
              >
                <div className="text-[11px] font-mono text-mute group-hover:text-blue uppercase truncate">
                  {t('overview.sourceVerification')}
                </div>
                <div className="mt-1">
                  {verificationResult?.status === 'cross_checked' ? (
                    <span className="text-xs font-mono font-bold text-ok px-1.5 py-0.5 rounded bg-ok/10">
                      {t('overview.statusCrossChecked')}
                    </span>
                  ) : verificationResult?.status === 'needs_review' ? (
                    <span className="text-xs font-mono font-bold text-amber-800 px-1.5 py-0.5 rounded bg-amber-500/10">
                      {t('overview.statusNeedsReview')}
                    </span>
                  ) : (
                    <span className="text-xs font-mono font-bold text-mute px-1.5 py-0.5 rounded bg-bg2">
                      {t('overview.statusUnverified')}
                    </span>
                  )}
                </div>
              </button>
            </div>

            <div className="pt-2 flex justify-end">
              <Button size="sm" variant="secondary" onClick={onGoToClauses}>
                {t('overview.viewAllClauses')} &rarr;
              </Button>
            </div>
          </div>
        </div>
      </GlassCard>

      {!!result.next_steps?.length && (
        <GlassCard className="p-5 space-y-3">
          <h3 className="font-bold text-navy">{t('overview.nextStepsTitle')}</h3>
          <p className="text-xs text-mute">{t('overview.nextStepsSub')}</p>
          {result.next_steps.map((step, index) => (
            <div key={index} className="text-sm text-navy space-y-1">
              <p>{step.text}</p>
              {step.clause_ids?.map((id) => (
                <Button
                  key={id}
                  size="sm"
                  variant="secondary"
                  onClick={() => onNavigateEvidence(id)}
                >
                  {t('overview.showInSource', { id })}
                </Button>
              ))}
            </div>
          ))}
        </GlassCard>
      )}

      {/* Needs Review or Skipped Clauses Section (if any) */}
      {needsReviewItems.length > 0 && (
        <GlassCard className="p-5 border-amber-500/30 bg-amber-500/5">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <h4 className="text-sm font-bold text-amber-900">
              {t('overview.reviewFindingsTitle', { count: needsReviewItems.length })}
            </h4>
          </div>
          <p className="text-xs text-amber-800 mb-3">
            {t('overview.reviewFindingsDescription')}
          </p>
          <div className="space-y-2">
            {needsReviewItems.map((item) => (
              <div
                key={item.item_id}
                className="flex items-center justify-between p-2.5 rounded bg-paper border border-line text-xs"
              >
                <div className="flex items-center gap-2">
                  <MonoLabel>{item.clause_id}</MonoLabel>
                  <span className="text-navy line-clamp-1">{item.explanation}</span>
                </div>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => onNavigateEvidence(item.clause_id)}
                >
                  {t('review.showInSource')}
                </Button>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* Warnings List */}
      {result.warnings && result.warnings.length > 0 && (
        <div className="space-y-2">
          {result.warnings.map((warning, idx) => (
            <Banner key={idx} variant="warn">
              {warning}
            </Banner>
          ))}
        </div>
      )}

      {/* Local Model Provenance (Technical Details) */}
      <div className="rounded-lg border border-line bg-paper overflow-hidden">
        <button
          type="button"
          onClick={() => setShowTechDetails((prev) => !prev)}
          className="w-full px-4 py-3 flex items-center justify-between text-xs font-mono font-medium text-mute hover:text-navy hover:bg-bg2/40 transition-colors cursor-pointer"
        >
          <span className="flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-blue" />
            {showTechDetails ? t('overview.hideTech') : t('overview.showTech')}: {t('overview.modelProvenance')}
          </span>
          {showTechDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showTechDetails && (
          <div className="p-4 pt-2 border-t border-line bg-bg2/30 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
            <div>
              <span className="text-mute block text-[10px] uppercase">{t('overview.classifierVer')}</span>
              <span className="text-navy font-semibold">{result.provenance.classifier_version}</span>
            </div>
            <div>
              <span className="text-mute block text-[10px] uppercase">{t('overview.generatorVer')}</span>
              <span className="text-navy font-semibold">{result.provenance.generator}</span>
            </div>
            <div>
              <span className="text-mute block text-[10px] uppercase">{t('overview.rulesVer')}</span>
              <span className="text-navy font-semibold">{result.provenance.rules_version}</span>
            </div>
          </div>
        )}
      </div>

      {/* Persistent Information Disclaimer Card */}
      <GlassCard className="p-5 border-blue/20 bg-blue/5">
        <div className="flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-blue shrink-0 mt-0.5" />
          <div className="space-y-2 text-xs">
            <h4 className="font-bold text-navy text-sm">
              {t('disclaimers.footer')}
            </h4>
            <p className="text-mute leading-relaxed">
              {t('disclaimers.noDetectedCue')}
            </p>
          </div>
        </div>
      </GlassCard>

      {/* Legal Aid Mini Card */}
      <GlassCard className="p-5 border-cyan/30 bg-paper">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold uppercase text-cyan px-2 py-0.5 rounded bg-cyan/10">
                {t('legalAid.freeAidTitle')}
              </span>
              <span className="text-xs font-bold text-navy">National Legal Services Authority (NALSA)</span>
            </div>
            <p className="text-xs text-mute">
              {t('legalAid.needHelp')}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex items-center gap-1.5 text-xs font-mono font-bold text-navy px-3 py-1.5 rounded bg-bg2 border border-line">
              <Phone className="w-3.5 h-3.5 text-blue" />
              <span>15100</span>
            </div>
            <a
              href="https://nalsa.gov.in/legal-aid/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded bg-blue text-white hover:bg-blue2 transition-colors"
            >
              <span>NALSA Portal</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};
export default OverviewSummaryPanel;
