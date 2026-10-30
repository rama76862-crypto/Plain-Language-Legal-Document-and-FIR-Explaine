/**
 * ResultExport Component (C-13)
 * Generates verified client-side Markdown exports and formatted Print layouts:
 * - Pure client-side generation via Blob (Never passes document tokens or secrets)
 * - Sanitized filename pattern: nyayasarathi-{filename}-r{revision}-{lang}.md
 * - Complete provenance, clause evidence, deadlines, and legal disclaimers
 * - User opt-in toggle for in-memory Q&A thread
 * - window.print() support with specialized print styling
 */

import React, { useState } from 'react';
import {
  Download,
  Printer,
  ShieldCheck,
  CheckSquare,
  Square,
  Lock,
} from 'lucide-react';
import { useResult } from './ResultContext';
import { useSession } from '../../lib/session';
import { GlassCard, Button, Banner } from '../../design/primitives';
import { downloadReviewReport } from '../../lib/api';
import { useT } from '../../lib/i18n';

export const ResultExport: React.FC = () => {
  const { t } = useT();
  const { result, outputLanguage, qaHistory } = useResult();
  const analysisId=result?.analysis_id??null;
  const { filename, revision, inputLanguage, documentId, sessionToken } = useSession();
  const [includeQuestions, setIncludeQuestions] = useState<boolean>(true);
  const [downloadSuccess, setDownloadSuccess] = useState<boolean>(false);
  const [reportError, setReportError] = useState<string | null>(null);
  const [reportBusy, setReportBusy] = useState(false);

  const downloadReport = async (format: 'json' | 'md' | 'html') => {
    if (!documentId || !sessionToken || !analysisId) return;
    setReportBusy(true); setReportError(null);
    try {
      const blob = await downloadReviewReport(documentId, sessionToken, analysisId, format, includeQuestions);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = `review-r${revision}-${outputLanguage}.${format}`;
      a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { setReportError(error instanceof Error ? error.message : 'Report download failed.'); }
    finally { setReportBusy(false); }
  };

  if (!result) return null;

  const sanitizeFilename = (name: string | null): string => {
    if (!name) return 'document';
    return name
      .replace(/\.[^/.]+$/, '') // strip extension
      .replace(/[^a-zA-Z0-9_-]/g, '_')
      .toLowerCase();
  };

  const handleDownloadMarkdown = () => {
    if (documentId && sessionToken && analysisId) {
      void downloadReport('md');
      return;
    }
    const cleanName = sanitizeFilename(filename);
    const downloadFilename = `nyayasarathi-${cleanName}-r${revision}-${outputLanguage}.md`;

    // Construct Markdown in memory
    const lines: string[] = [];

    // Header
    lines.push('# NyayaSarathi Plain-Language Legal Document Explanation\n');
    lines.push(
      '> **Statutory Disclaimer**: NyayaSarathi gives general information to help you understand a document. ' +
        'It is not legal advice and does not replace a qualified advocate. No detected cue is not a clean legal ' +
        'bill of health. Always read every clause carefully.\n'
    );

    // Metadata
    lines.push('## Document Overview');
    lines.push(`- **Source Document**: ${filename || 'Uploaded Document'}`);
    lines.push(`- **Document Revision**: ${revision}`);
    lines.push(`- **Document Type**: ${result.document_type.toUpperCase()}`);
    lines.push(`- **Original Input Language**: ${inputLanguage.toUpperCase()}`);
    lines.push(`- **Explanation Language**: ${outputLanguage.toUpperCase()}`);
    lines.push(`- **Analysis Generated**: ${new Date().toISOString()}`);
    lines.push(`- **Clause Coverage**: Analysed ${result.coverage.analysed} of ${result.coverage.total} clauses\n`);

    // Warnings if present
    if (result.warnings && result.warnings.length > 0) {
      lines.push('### Analysis Notices');
      result.warnings.forEach((w) => lines.push(`- ${w}`));
      lines.push('');
    }

    // Clause explanations
    lines.push('## Clause-by-Clause Explanations\n');
    result.items.forEach((item) => {
      lines.push(`### Clause ${item.clause_id}`);
      if (item.kind === 'attention') {
        lines.push(`- **Potential Concern**: ${item.category?.replace(/_/g, ' ') || 'Attention'}`);
      } else if (item.kind === 'allegation') {
        lines.push(`- **Allegation recorded in FIR** (Not a finding of guilt)`);
      } else if (item.kind === 'notice_action') {
        lines.push(`- **Action Demanded by Notice**`);
      }

      lines.push(`- **Plain-Language Explanation**: ${item.explanation}`);
      lines.push(`- **Review Status**: ${item.review_status}`);

      if (item.evidence && item.evidence.length > 0) {
        item.evidence.forEach((ev) => {
          lines.push(`- **Original Source Quote**: "${ev.quote}"`);
        });
      }

      if (item.limitations && item.limitations.length > 0) {
        lines.push(`- **Limitations**: ${item.limitations.join(', ')}`);
      }

      if (item.reference_ids && item.reference_ids.length > 0) {
        const refs = item.reference_ids
          .map((id) => result.references?.find((r) => r.reference_id === id))
          .filter(Boolean);
        if (refs.length > 0) {
          lines.push(
            `- **Statutory References**: ${refs
              .map((r) => `${r?.title} (${r?.section})`)
              .join(', ')}`
          );
        }
      }

      lines.push('');
    });

    // Deadlines & Timeline
    lines.push('## Deadlines & Timeline\n');
    if (result.deadlines.length === 0) {
      lines.push('No explicit dates or time periods detected. Please review all clauses.\n');
    } else {
      result.deadlines.forEach((d) => {
        if (d.status === 'explicit') {
          lines.push(`- **[Explicit Date]** ${d.display_text} (Clause ${d.clause_id})`);
          lines.push(`  - Source: "${d.source_quote}"`);
        } else if (d.status === 'needs_information') {
          lines.push(
            `- **[Relative Time Period]** ${d.display_text} — Starts from: ${d.anchor?.replace(/_/g, ' ') || 'event'} (Clause ${d.clause_id})`
          );
          lines.push(`  - Source: "${d.source_quote}"`);
          if (d.missing_information && d.missing_information.length > 0) {
            lines.push(`  - *Missing outside information*: ${d.missing_information.join(', ')}`);
          }
          lines.push(
            '  - *Notice: This document counts days from an event that is not in the file. The app does not calculate legal deadlines.*'
          );
        } else {
          lines.push(`- **[Verify Date]** ${d.display_text} (Clause ${d.clause_id})`);
        }
      });
      lines.push('');
    }

    // Questions & Answers (if requested)
    if (includeQuestions && qaHistory.length > 0) {
      lines.push('## Document Questions & Answers\n');
      lines.push('*The following questions were asked in-memory during this session against this reviewed document revision:*\n');
      qaHistory.forEach((qa, idx) => {
        lines.push(`### Q${idx + 1}: ${qa.question}`);
        if (qa.answer) {
          lines.push(`- **Explanation**: ${qa.answer.answer}`);
          lines.push(`- **Review Status**: ${qa.answer.review_status}`);
          if (qa.answer.evidence && qa.answer.evidence.length > 0) {
            qa.answer.evidence.forEach((ev) => {
              lines.push(`- **Source Evidence (Clause ${ev.clause_id})**: "${ev.quote}"`);
            });
          }
          if (qa.answer.limitations && qa.answer.limitations.length > 0) {
            lines.push(`- **Limitations**: ${qa.answer.limitations.join(', ')}`);
          }
        } else if (qa.error) {
          lines.push(`- *Status: Question error (${qa.error.message})*`);
        }
        lines.push('');
      });
    }

    // Provenance
    lines.push('## Local Model Provenance');
    lines.push(`- Classifier Engine: ${result.provenance.classifier_version}`);
    lines.push(`- Text Generator: ${result.provenance.generator}`);
    lines.push(`- Rules Version: ${result.provenance.rules_version}\n`);

    // Legal Aid Resources
    lines.push('## Free Legal Aid Directory');
    lines.push('- **NALSA Toll-Free Helpline**: 15100');
    lines.push('- **Official NALSA Portal**: https://nalsa.gov.in/legal-aid/');
    lines.push(
      '- Free legal aid is available through District Legal Services Authorities (DLSA) ' +
        'for eligible citizens. Eligibility is decided by the authority.\n'
    );

    // Final security note
    lines.push('---');
    lines.push(
      '*Generated by the configured NyayaSarathi processing server. Review generated explanations against the original document.*'
    );

    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Immediate cleanup
    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 100);

    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 4000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-2 border-b border-line space-y-1">
        <h3 className="text-sm font-bold text-navy flex items-center gap-2">
          <Download className="w-4 h-4 text-blue" />
          {t('export.title')}
        </h3>
        <p className="text-xs text-mute">
          {t('export.sub')}
        </p>
      </div>

      <GlassCard className="p-6 space-y-3">
        <h4 className="text-sm font-bold text-navy">Analysis review report</h4>
        <p className="text-xs text-mute">Automatically prepared by the backend. Includes source facts, failed coverage, uncertainty, deadlines and optional questions. This is an automated report, not approval by a legal reviewer.</p>
        <div className="flex flex-wrap gap-2">
          {(['md', 'json', 'html'] as const).map(format => <Button key={format} disabled={reportBusy} onClick={() => downloadReport(format)}>{format.toUpperCase()}</Button>)}
        </div>
        {reportError && <Banner variant="error" title="Report unavailable">{reportError}</Banner>}
      </GlassCard>

      {/* Export Options Card */}
      <GlassCard className="p-6 space-y-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-navy">{t('export.downloadMd')}</h4>
            <p className="text-xs text-mute">
              Plain text with headings, source quotations, review warnings and any admitted references.
            </p>
          </div>

          <Button
            variant="primary"
            size="md"
            onClick={() => analysisId && documentId && sessionToken ? downloadReport('md') : handleDownloadMarkdown()}
            className="shrink-0"
          >
            <Download className="w-4 h-4" />
            <span>{t('export.downloadMd')}</span>
          </Button>
        </div>

        {downloadSuccess && (
          <Banner variant="info" title="Download Complete">
            Markdown file downloaded. It is stored directly on your device.
          </Banner>
        )}

        {/* Q&A Opt-In Checkbox */}
        <div className="pt-3 border-t border-line flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIncludeQuestions(!includeQuestions)}
            className="text-navy flex items-center gap-2 text-xs font-medium cursor-pointer"
          >
            {includeQuestions ? (
              <CheckSquare className="w-4 h-4 text-blue shrink-0" />
            ) : (
              <Square className="w-4 h-4 text-mute shrink-0" />
            )}
            <span>
              {t('export.includeQa')}
              {qaHistory.length > 0
                ? ` (${qaHistory.length})`
                : ''}
            </span>
          </button>
        </div>

        <div className="text-[11px] text-mute flex items-center gap-1.5 font-mono pt-1">
          <Lock className="w-3.5 h-3.5 text-ok" />
          <span>{t('export.localDeviceNote')}</span>
        </div>
      </GlassCard>

      {/* Print View Card */}
      <GlassCard className="p-6 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-navy">{t('export.printButton')}</h4>
            <p className="text-xs text-mute">
              Formatted clean layout optimized for A4/Letter paper with high-contrast text.
            </p>
          </div>

          <Button
            variant="secondary"
            size="md"
            onClick={handlePrint}
            className="shrink-0"
          >
            <Printer className="w-4 h-4" />
            <span>{t('export.printButton')}</span>
          </Button>
        </div>
      </GlassCard>

      {/* Privacy Guarantee Banner */}
      <div className="p-4 rounded-lg bg-bg2/60 border border-line text-xs space-y-2">
        <div className="flex items-center gap-2 font-bold text-navy">
          <ShieldCheck className="w-4 h-4 text-ok" />
          <span>No Session Leaks</span>
        </div>
        <p className="text-mute leading-relaxed">
          Reports contain your document text and generated results. Keep downloaded copies private.
          Session tokens and internal service addresses are excluded from the report format.
        </p>
      </div>

      {/* Print-Only Formatted Layout */}
      <div className="hidden print:block print:p-8 space-y-6 text-black bg-white">
        <div className="border-b-2 border-black pb-4 space-y-2">
          <h1 className="text-xl font-bold">NyayaSarathi Plain-Language Explanation</h1>
          <p className="text-xs text-gray-600">
            Information only. This is not legal advice and does not replace a qualified advocate.
          </p>
          <div className="grid grid-cols-2 gap-2 text-xs pt-2 font-mono">
            <div><strong>Document:</strong> {filename || 'Uploaded Document'} (Rev {revision})</div>
            <div><strong>Type:</strong> {result.document_type.toUpperCase()}</div>
            <div><strong>Input Language:</strong> {inputLanguage.toUpperCase()}</div>
            <div><strong>Explanation Language:</strong> {outputLanguage.toUpperCase()}</div>
            <div><strong>Coverage:</strong> Analysed {result.coverage.analysed} of {result.coverage.total} clauses</div>
            <div><strong>Date:</strong> {new Date().toLocaleDateString()}</div>
          </div>
        </div>

        {/* Clauses */}
        <div className="space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider border-b border-gray-300 pb-1">
            Clause-by-Clause Explanations
          </h2>
          {result.items.map((item) => (
            <div key={item.item_id} className="text-xs space-y-1 pb-3 border-b border-gray-200">
              <div className="font-bold">
                Clause {item.clause_id} {item.category ? `[${item.category.replace(/_/g, ' ')}]` : ''} ({item.review_status})
              </div>
              <div>{item.explanation}</div>
              {item.evidence?.map((ev, i) => (
                <blockquote key={i} className="pl-3 border-l-2 border-gray-400 italic text-gray-700">
                  "{ev.quote}"
                </blockquote>
              ))}
            </div>
          ))}
        </div>

        {/* Deadlines */}
        {result.deadlines.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-bold uppercase tracking-wider border-b border-gray-300 pb-1">
              Dates and Deadlines
            </h2>
            {result.deadlines.map((d) => (
              <div key={d.deadline_id} className="text-xs space-y-0.5">
                <span className="font-semibold">{d.display_text}</span> (Clause {d.clause_id})
                <div className="italic text-gray-600">"{d.source_quote}"</div>
              </div>
            ))}
          </div>
        )}

        {/* Q&A in Print if requested */}
        {includeQuestions && qaHistory.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-sm font-bold uppercase tracking-wider border-b border-gray-300 pb-1">
              Questions & Answers ({qaHistory.length})
            </h2>
            {qaHistory.map((qa, idx) => (
              <div key={qa.id || idx} className="text-xs space-y-1 pb-2 border-b border-gray-200">
                <div className="font-bold">Q: {qa.question}</div>
                {qa.answer ? (
                  <>
                    <div>A: {qa.answer.answer}</div>
                    {qa.answer.evidence?.map((ev, i) => (
                      <div key={i} className="italic text-gray-600 pl-2">Evidence: "{ev.quote}"</div>
                    ))}
                  </>
                ) : (
                  <div className="italic text-red-600">Error: {qa.error?.message}</div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="pt-4 border-t border-gray-300 text-[10px] text-gray-500 flex justify-between">
          <span>NyayaSarathi Civic Legal Empowerment · NALSA Helpline: 15100</span>
          <span>Zero cloud persistence</span>
        </div>
      </div>
    </div>
  );
};
export default ResultExport;
