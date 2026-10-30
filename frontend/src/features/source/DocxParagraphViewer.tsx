/**
 * DocxParagraphViewer Component
 * Safe, structured viewer for DOCX files:
 * - Strictly avoids executing or rendering arbitrary DOCX HTML
 * - Displays numbered paragraphs with paragraph_index ("¶ 1", "¶ 2")
 * - Strictly forbids fabricating or displaying page numbers for DOCX
 * - Highlights target paragraph upon clause selection
 */

import React, { useRef, useEffect, useCallback, useImperativeHandle } from 'react';
import type { Clause } from '../../lib/types';
import { MonoLabel } from '../../design/primitives';
import { announceToScreenReader } from '../../lib/a11y';

export interface DocxViewerRef {
  scrollToParagraph: (paragraphIndex: number) => void;
  highlightClause: (clause: Clause) => void;
}

interface DocxParagraphViewerProps {
  clauses: Clause[];
  activeClause?: Clause | null;
}

export const DocxParagraphViewer = React.forwardRef<DocxViewerRef, DocxParagraphViewerProps>(
  ({ clauses, activeClause }, ref) => {
    const containerRef = useRef<HTMLDivElement | null>(null);

    const scrollToParagraph = useCallback((pIndex: number) => {
      const el = document.getElementById(`docx-para-${pIndex}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, []);

    const highlightClause = useCallback(
      (clause: Clause) => {
        const pIndex = clause.source_ref.paragraph_index;
        if (pIndex) {
          scrollToParagraph(pIndex);
          announceToScreenReader(`Showing clause ${clause.clause_id} in paragraph ${pIndex}`);
        }
      },
      [scrollToParagraph]
    );

    useImperativeHandle(ref, () => ({
      scrollToParagraph,
      highlightClause,
    }));

    useEffect(() => {
      if (activeClause) {
        highlightClause(activeClause);
      }
    }, [activeClause, highlightClause]);

    return (
      <div
        ref={containerRef}
        className="w-full h-full overflow-y-auto p-6 space-y-4 select-text"
      >
        <div className="p-3 bg-bg2/60 border border-line rounded text-xs text-mute flex items-center justify-between">
          <MonoLabel>EXTRACTED PARAGRAPHS (DOCX)</MonoLabel>
          <span className="font-mono text-[11px] font-semibold text-navy">
            {clauses.length} Paragraphs
          </span>
        </div>

        {clauses.map((c, idx) => {
          const pIndex = c.source_ref.paragraph_index || idx + 1;
          const isActive = activeClause?.clause_id === c.clause_id;

          return (
            <div
              key={c.clause_id}
              id={`docx-para-${pIndex}`}
              data-evidence-target={isActive ? 'active' : undefined}
              className={`p-4 rounded-md border transition-all text-sm leading-relaxed ${
                isActive
                  ? 'bg-blue/10 border-blue ring-2 ring-cyan/40 shadow-sm'
                  : 'bg-paper border-line hover:border-blue/30'
              }`}
            >
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-line/40 text-xs text-mute font-mono">
                <span className="font-bold text-navy">¶ {pIndex}</span>
                <span className="text-[10px] uppercase">{c.extraction_method}</span>
              </div>
              {/* Escaped plain text */}
              <p className="text-ink whitespace-pre-wrap">{c.source_text}</p>
            </div>
          );
        })}
      </div>
    );
  }
);
DocxParagraphViewer.displayName = 'DocxParagraphViewer';
