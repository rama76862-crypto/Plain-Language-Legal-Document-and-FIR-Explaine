/**
 * SourceDocumentViewer Component (C-05)
 * Left pane of the synchronized split workspace:
 * - Direct PDF.js canvas rendering with coordinate bounding box highlights
 * - DOCX paragraph numbered structure with ¶ labels (never fabricated pages)
 * - Zoom controls, page navigator, and fallback floating quote card
 * - Memory cleanup: revokes object URLs on unmount
 */

import { useState, useRef, useImperativeHandle, forwardRef } from 'react';
import type { Clause } from '../../lib/types';
import { PdfViewerCanvas, PdfViewerRef } from './PdfViewerCanvas';
import { DocxParagraphViewer, DocxViewerRef } from './DocxParagraphViewer';
import { EvidenceBeam } from '../../design/scenes/EvidenceBeam';
import { MonoLabel, Button } from '../../design/primitives';
import { FileText, ZoomIn, ZoomOut, Maximize2, ChevronLeft, ChevronRight, Quote } from 'lucide-react';
import { useT } from '../../lib/i18n';

export interface SourceDocumentViewerRef {
  scrollToClause: (clauseId: string) => void;
}

interface SourceDocumentViewerProps {
  filename?: string | null;
  blobUrl?: string | null;
  clauses?: Clause[];
  activeClauseId?: string | null;
  className?: string;
}

export const SourceDocumentViewer = forwardRef<SourceDocumentViewerRef, SourceDocumentViewerProps>(
  (
    {
      filename = 'document.pdf',
      blobUrl,
      clauses = [],
      activeClauseId,
      className = '',
    },
    ref
  ) => {
    const { t } = useT();
    const pdfRef = useRef<PdfViewerRef | null>(null);
    const docxRef = useRef<DocxViewerRef | null>(null);

    const [zoomScale, setZoomScale] = useState<number>(1.0);
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [totalPages, setTotalPages] = useState<number>(1);

    const isDocx = filename ? filename.toLowerCase().endsWith('.docx') : false;
    const activeClause = clauses.find((c) => c.clause_id === activeClauseId) || null;

    useImperativeHandle(ref, () => ({
      scrollToClause: (clauseId: string) => {
        const target = clauses.find((c) => c.clause_id === clauseId);
        if (!target) return;

        if (isDocx) {
          docxRef.current?.highlightClause(target);
        } else {
          pdfRef.current?.highlightClause(target);
        }
      },
    }));

    const handleZoomIn = () => setZoomScale((z) => Math.min(2.0, z + 0.15));
    const handleZoomOut = () => setZoomScale((z) => Math.max(0.6, z - 0.15));
    const handleResetZoom = () => setZoomScale(1.0);

    const handlePrevPage = () => {
      const p = Math.max(1, currentPage - 1);
      setCurrentPage(p);
      pdfRef.current?.scrollToPage(p);
    };

    const handleNextPage = () => {
      const p = Math.min(totalPages, currentPage + 1);
      setCurrentPage(p);
      pdfRef.current?.scrollToPage(p);
    };

    return (
      <div className={`relative flex flex-col h-full bg-bg2/40 border-r border-line ${className}`}>
        {/* Pane Header */}
        <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-paper/90 border-b border-line">
          <div className="flex items-center gap-2 truncate">
            <FileText className="w-4 h-4 text-blue shrink-0" aria-hidden="true" />
            <div className="flex flex-col truncate">
              <span className="text-xs font-bold text-navy truncate">{filename}</span>
              <MonoLabel>{t('source.originalDocument')}</MonoLabel>
            </div>
          </div>

          {/* Controls: Zoom & Page Navigation */}
          <div className="flex items-center gap-2">
            {!isDocx && (
              <>
                <div className="flex items-center gap-1 bg-bg2 rounded px-2 py-1 text-xs font-mono text-mute">
                  <button
                    type="button"
                    onClick={handlePrevPage}
                    disabled={currentPage <= 1}
                    className="hover:text-ink disabled:opacity-40"
                    aria-label={t('source.prevPage')}
                  >
                    <ChevronLeft className="w-3.5 h-3.5" />
                  </button>
                  <span>
                    {currentPage} / {totalPages}
                  </span>
                  <button
                    type="button"
                    onClick={handleNextPage}
                    disabled={currentPage >= totalPages}
                    className="hover:text-ink disabled:opacity-40"
                    aria-label={t('source.nextPage')}
                  >
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>

                <div className="flex items-center gap-0.5 bg-bg2 rounded p-0.5">
                  <Button variant="ghost" size="sm" onClick={handleZoomOut} aria-label={t('source.zoomOut')}>
                    <ZoomOut className="w-3.5 h-3.5 text-mute" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleResetZoom} aria-label={t('source.resetZoom')}>
                    <Maximize2 className="w-3.5 h-3.5 text-mute" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={handleZoomIn} aria-label={t('source.zoomIn')}>
                    <ZoomIn className="w-3.5 h-3.5 text-mute" />
                  </Button>
                </div>
              </>
            )}

            <div className="px-2 py-0.5 rounded-pill bg-paper border border-line text-[10px] font-mono text-mute">
              {t('source.localMemory')}
            </div>
          </div>
        </div>

        {/* Content Viewer Body */}
        <div className="flex-1 relative overflow-hidden">
          {isDocx ? (
            <DocxParagraphViewer
              ref={docxRef}
              clauses={clauses}
              activeClause={activeClause}
            />
          ) : blobUrl ? (
            <PdfViewerCanvas
              ref={pdfRef}
              blobUrl={blobUrl}
              activeClause={activeClause}
              zoomScale={zoomScale}
              onPageCountChange={setTotalPages}
              onCurrentPageChange={setCurrentPage}
            />
          ) : clauses.length > 0 ? (
            <DocxParagraphViewer
              ref={docxRef}
              clauses={clauses}
              activeClause={activeClause}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-xs text-mute font-mono">
              {t('source.loading')}
            </div>
          )}

          {/* Fallback Floating Quote Card when BBOX is null or page-level navigation used */}
          {activeClause && !activeClause.source_ref.bbox && !isDocx && (
            <div className="absolute bottom-4 left-4 right-4 z-30 p-3 bg-paper/95 backdrop-blur-md rounded-md shadow-card border border-blue/40 text-xs text-ink space-y-1 animate-fade-in">
              <div className="flex items-center justify-between text-mute font-mono text-[10px]">
                <span className="font-bold text-navy flex items-center gap-1">
                  <Quote className="w-3 h-3 text-blue" />
                  Clause {activeClause.clause_id} (Page {activeClause.source_ref.page_number || 1})
                </span>
                <span>{t('source.pageCitation')}</span>
              </div>
              <p className="text-mute">{t('source.reviewedQuote')}</p>
              <p className="line-clamp-3 text-ink italic font-serif">
                "{activeClause.reviewed_text}"
              </p>
            </div>
          )}
        </div>

        {/* Interactive Evidence Beam Connecting Button to Source Highlight */}
        <EvidenceBeam />
      </div>
    );
  }
);
SourceDocumentViewer.displayName = 'SourceDocumentViewer';
export default SourceDocumentViewer;
