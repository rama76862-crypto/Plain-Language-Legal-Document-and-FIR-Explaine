/**
 * PdfViewerCanvas Component
 * Direct PDF.js canvas renderer:
 * - Worker bundled locally via Vite ?url import
 * - Converts PDF points [x0, y0, x1, y1] (origin bottom-left) to viewport canvas pixels
 * - Displays pulse ring animation on active highlighted clause
 * - Memory hygiene: cancels render tasks and destroys PDF document on unmount
 */

import React, { useEffect, useRef, useState, useCallback, useImperativeHandle } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import type { Clause } from '../../lib/types';
import { Skeleton } from '../../design/primitives';
import { announceToScreenReader } from '../../lib/a11y';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

export interface PdfViewerRef {
  scrollToPage: (pageNum: number) => void;
  highlightClause: (clause: Clause) => void;
}

interface PdfViewerCanvasProps {
  blobUrl: string;
  activeClause?: Clause | null;
  zoomScale?: number;
  onPageCountChange?: (total: number) => void;
  onCurrentPageChange?: (current: number) => void;
}

export const PdfViewerCanvas = React.forwardRef<PdfViewerRef, PdfViewerCanvasProps>(
  (
    {
      blobUrl,
      activeClause,
      zoomScale = 1.0,
      onPageCountChange,
      onCurrentPageChange,
    },
    ref
  ) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
    const [numPages, setNumPages] = useState<number>(0);
    const [loading, setLoading] = useState<boolean>(true);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [highlightBbox, setHighlightBbox] = useState<{
      pageNum: number;
      left: number;
      top: number;
      width: number;
      height: number;
    } | null>(null);

    const activeRenderTasks = useRef<Map<number, pdfjsLib.RenderTask>>(new Map());

    // 1. Load PDF Document from Blob URL
    useEffect(() => {
      setLoading(true);
      setLoadError(null);

      const controller=new AbortController();
      let loadingTask:pdfjsLib.PDFDocumentLoadingTask|undefined;
      // Read the already authenticated in-memory blob ourselves. PDF.js's URL
      // transport parses response headers and fails on some embedded browsers.
      fetch(blobUrl,{signal:controller.signal,cache:'no-store'})
        .then(response => {if(!response.ok) throw new Error('Source PDF unavailable'); return response.arrayBuffer();})
        .then(bytes => {
          if(controller.signal.aborted) throw new DOMException('Cancelled','AbortError');
          loadingTask=pdfjsLib.getDocument({data:new Uint8Array(bytes)});
          return loadingTask.promise;
        })
        .then((doc) => {
          if(controller.signal.aborted) {void doc.destroy();return;}
          setPdfDoc(doc);
          setNumPages(doc.numPages);
          onPageCountChange?.(doc.numPages);
          setLoading(false);
        })
        .catch((err) => {
          if(controller.signal.aborted) return;
          setLoadError(err instanceof Error ? err.message : 'Failed to load PDF source');
          setLoading(false);
        });

      return () => {
        controller.abort();
        void loadingTask?.destroy();
      };
    }, [blobUrl, onPageCountChange]);

    // 2. Render Page Canvas
    const renderPage = useCallback(
      async (pageNum: number, canvasEl: HTMLCanvasElement) => {
        if (!pdfDoc) return;

        // Cancel previous task on this page
        if (activeRenderTasks.current.has(pageNum)) {
          activeRenderTasks.current.get(pageNum)?.cancel();
          activeRenderTasks.current.delete(pageNum);
        }

        try {
          const page = await pdfDoc.getPage(pageNum);
          const viewport = page.getViewport({ scale: zoomScale * 1.5 }); // HiDPI factor 1.5
          const ctx = canvasEl.getContext('2d');
          if (!ctx) return;

          canvasEl.width = viewport.width;
          canvasEl.height = viewport.height;
          canvasEl.style.width = `${viewport.width / 1.5}px`;
          canvasEl.style.height = `${viewport.height / 1.5}px`;

          const renderContext = {
            canvasContext: ctx,
            viewport,
          };

          const task = page.render(renderContext);
          activeRenderTasks.current.set(pageNum, task);
          await task.promise;
          activeRenderTasks.current.delete(pageNum);
        } catch (err: unknown) {
          if (err instanceof Error && err.name !== 'RenderingCancelledException') {
            // Cancelled exception is normal during rapid zoom/scroll
          }
        }
      },
      [pdfDoc, zoomScale]
    );

    // 3. Scroll to specific page
    const scrollToPage = useCallback((pageNum: number) => {
      const pageEl = document.getElementById(`pdf-page-wrapper-${pageNum}`);
      if (pageEl && containerRef.current) {
        pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, []);

    // 4. Highlight clause coordinate bbox
    const highlightClause = useCallback(
      async (clause: Clause) => {
        if (!clause.source_ref.page_number || !pdfDoc) return;
        const pageNum = clause.source_ref.page_number;

        scrollToPage(pageNum);
        announceToScreenReader(`Showing clause ${clause.clause_id} on page ${pageNum}`);

        if (clause.source_ref.bbox) {
          try {
            const [x0, y0, x1, y1] = clause.source_ref.bbox;

            // BE1/PyMuPDF supplies top-left PDF-point coordinates.
            const left = x0 * zoomScale;
            // BE1/PyMuPDF uses top-left coordinates, matching the viewer overlay.
            const top = y0 * zoomScale;
            const width = (x1 - x0) * zoomScale;
            const height = (y1 - y0) * zoomScale;

            setHighlightBbox({
              pageNum,
              left,
              top,
              width,
              height,
            });
          } catch {
            setHighlightBbox(null);
          }
        } else {
          setHighlightBbox(null);
        }
      },
      [pdfDoc, zoomScale, scrollToPage]
    );

    useImperativeHandle(ref, () => ({
      scrollToPage,
      highlightClause,
    }));

    // Trigger highlight when activeClause prop updates
    useEffect(() => {
      if (activeClause) {
        highlightClause(activeClause);
      }
    }, [activeClause, highlightClause]);

    if (loading) {
      return (
        <div className="p-8 space-y-4">
          <Skeleton className="h-[500px] w-full rounded-md" />
        </div>
      );
    }

    if (loadError) {
      return (
        <div className="p-8 text-center space-y-3">
          <div className="text-concern font-bold text-sm">Failed to load original PDF</div>
          <p className="text-xs text-mute font-mono">{loadError}</p>
        </div>
      );
    }

    return (
      <div
        ref={containerRef}
        className="w-full h-full overflow-y-auto flex flex-col items-center gap-6 p-6 select-none"
      >
        {Array.from({ length: numPages }, (_, idx) => idx + 1).map((pageNum) => (
          <div
            key={pageNum}
            id={`pdf-page-wrapper-${pageNum}`}
            className="relative bg-paper shadow-card border border-line rounded-md overflow-hidden"
            onMouseEnter={() => onCurrentPageChange?.(pageNum)}
          >
            <PageCanvas pageNum={pageNum} renderPage={renderPage} />

            {/* Coordinate Bounding Box Overlay */}
            {highlightBbox && highlightBbox.pageNum === pageNum && (
              <div
                data-evidence-target="active"
                className="absolute z-20 pointer-events-none rounded transition-all duration-300"
                style={{
                  left: `${highlightBbox.left}px`,
                  top: `${highlightBbox.top}px`,
                  width: `${highlightBbox.width}px`,
                  height: `${highlightBbox.height}px`,
                  backgroundColor: 'rgba(47, 107, 255, 0.28)',
                  border: '2px solid var(--blue)',
                }}
              >
                <div className="absolute -inset-1 rounded border-2 border-cyan animate-ping opacity-75" />
              </div>
            )}

            {/* Micro Page Label */}
            <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-navy/70 text-white font-mono text-[10px]">
              Page {pageNum}
            </div>
          </div>
        ))}
      </div>
    );
  }
);
PdfViewerCanvas.displayName = 'PdfViewerCanvas';

const PageCanvas: React.FC<{
  pageNum: number;
  renderPage: (num: number, el: HTMLCanvasElement) => void;
}> = ({ pageNum, renderPage }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (canvasRef.current) {
      renderPage(pageNum, canvasRef.current);
    }
  }, [pageNum, renderPage]);

  return <canvas ref={canvasRef} className="block" />;
};
