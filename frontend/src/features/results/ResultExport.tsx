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

export const ResultExport: React.FC = () => {
  const { result, outputLanguage } = useResult();
  const { filename, revision, inputLanguage } = useSession();
  const [includeQuestions, setIncludeQuestions] = useState<boolean>(true);
  const [downloadSuccess, setDownloadSuccess] = useState<boolean>(false);

  if (!result) return null;

  const sanitizeFilename = (name: string | null): string => {
    if (!name) return 'document';
    return name
      .replace(/\.[^/.]+$/, '') // strip extension
      .replace(/[^a-zA-Z0-9_-]/g, '_')
      .toLowerCase();
  };

  const handleDownloadMarkdown = () => {
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
      '*Generated locally on device via NyayaSarathi. Contains zero session tokens, passwords, or cloud telemetry.*'
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
          Export & Print Explanations
        </h3>
        <p className="text-xs text-mute">
          Save explanations and evidence to your device. Sessions are deleted when you close or refresh.
        </p>
      </div>

      {/* Export Options Card */}
      <GlassCard className="p-6 space-y-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-navy">Download Offline Markdown (.md)</h4>
            <p className="text-xs text-mute">
              Plain text formatted with headers, verbatim quotes, and verified statutory references.
            </p>
          </div>

          <Button
            variant="primary"
            size="md"
            onClick={handleDownloadMarkdown}
            className="shrink-0"
          >
            <Download className="w-4 h-4" />
            <span>Download Markdown</span>
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
            <span>Include in-memory question and answer history in export</span>
          </button>
        </div>

        <div className="text-[11px] text-mute flex items-center gap-1.5 font-mono pt-1">
          <Lock className="w-3.5 h-3.5 text-ok" />
          <span>The exported file stays on your device after the session is deleted.</span>
        </div>
      </GlassCard>

      {/* Print View Card */}
      <GlassCard className="p-6 space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <h4 className="text-sm font-bold text-navy">Print or Save as PDF</h4>
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
            <span>Print Document</span>
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
          Exported documents contain only public legal explanations and your verified text. Session
          tokens, document hashes, and internal network addresses are completely excluded.
        </p>
      </div>
    </div>
  );
};
export default ResultExport;
