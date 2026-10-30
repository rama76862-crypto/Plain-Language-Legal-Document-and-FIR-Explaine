/**
 * UploadDropzone Component (C-03)
 * Handles PDF and DOCX file selection and pre-flight validation:
 * - Drag-and-drop, file picker, and keyboard accessibility (Enter/Space)
 * - Enforces 10MB limit and 0-byte rejection
 * - Client-side page count warning via pdfjs-dist (>20 pages warning)
 * - Accessible error notifications with aria-live
 */

import React, { useState, useRef, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import pdfjsWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { useT } from '../../lib/i18n';
import { FileText, UploadCloud, X, AlertCircle } from 'lucide-react';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

interface UploadDropzoneProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  disabled?: boolean;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({
  selectedFile,
  onFileSelect,
  disabled = false,
}) => {
  const { t } = useT();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [pageWarning, setPageWarning] = useState<string | null>(null);

  const validateAndSetFile = useCallback(
    async (file: File) => {
      setErrorMsg(null);
      setPageWarning(null);

      // 1. Check 0-byte empty file
      if (file.size === 0) {
        setErrorMsg(t('errors.EMPTY_DOCUMENT'));
        onFileSelect(null);
        return;
      }

      // 2. Check maximum 10MB size limit
      if (file.size > MAX_BYTES) {
        setErrorMsg(t('errors.FILE_TOO_LARGE'));
        onFileSelect(null);
        return;
      }

      // 3. Check MIME type and file extension
      const fileNameLower = file.name.toLowerCase();
      const isPdf = fileNameLower.endsWith('.pdf') || file.type === 'application/pdf';
      const isDocx =
        fileNameLower.endsWith('.docx') ||
        file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

      if (!isPdf && !isDocx) {
        setErrorMsg(t('errors.UNSUPPORTED_FILE'));
        onFileSelect(null);
        return;
      }

      // 4. Client-side PDF page count inspection (warning only; does not block)
      if (isPdf) {
        try {
          const buffer = await file.arrayBuffer();
          const loadingTask = pdfjsLib.getDocument({ data: buffer });
          const pdfDoc = await loadingTask.promise;
          const numPages = pdfDoc.numPages;

          if (numPages > 20) {
            setPageWarning(t('upload.pageLimitWarning', { pages: numPages }));
          }
        } catch {
          // If client-side check fails, do not block; backend will validate
        }
      }

      onFileSelect(file);
    },
    [onFileSelect, t]
  );

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (disabled) return;
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-3">
      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={handleFileInputChange}
        className="hidden"
        disabled={disabled}
      />

      {/* Drop Zone Box */}
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="File upload dropzone. Press Enter or Space to choose a file."
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        className={`relative flex flex-col items-center justify-center p-8 text-center rounded-lg border-2 border-dashed transition-all cursor-pointer outline-none select-none ${
          isDragOver
            ? 'border-cyan bg-cyan/5 scale-[1.01]'
            : selectedFile
            ? 'border-blue/40 bg-blue/5'
            : 'border-line hover:border-blue/40 hover:bg-bg2/50'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        {selectedFile ? (
          <div className="flex items-center gap-3 w-full max-w-md p-3 bg-paper rounded-md border border-line shadow-sm">
            <FileText className="w-8 h-8 text-blue shrink-0" aria-hidden="true" />
            <div className="flex-1 text-left truncate">
              <div className="font-semibold text-sm text-navy truncate">
                {selectedFile.name}
              </div>
              <div className="font-mono text-xs text-mute">
                {formatFileSize(selectedFile.size)}
              </div>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onFileSelect(null);
                setPageWarning(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
              className="p-1 rounded hover:bg-bg2 text-mute hover:text-ink transition-colors"
              aria-label="Remove selected file"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="w-12 h-12 rounded-full bg-blue/10 flex items-center justify-center mx-auto text-blue">
              <UploadCloud className="w-6 h-6" aria-hidden="true" />
            </div>
            <div className="font-bold text-sm text-navy">{t('upload.dropTitle')}</div>
            <div className="text-xs text-mute">{t('upload.dropSub')}</div>
            <div className="font-mono text-[11px] text-mute pt-1 font-semibold tracking-wide">
              {t('upload.limitsNotice')}
            </div>
          </div>
        )}
      </div>

      {/* Accessible Error Announcements */}
      <div aria-live="assertive">
        {errorMsg && (
          <div className="flex items-center gap-2 p-2.5 rounded bg-concern-bg text-concern-ink text-xs font-semibold border border-concern/30">
            <AlertCircle className="w-4 h-4 shrink-0 text-concern" aria-hidden="true" />
            <span>{errorMsg}</span>
          </div>
        )}
        {pageWarning && (
          <div className="flex items-center gap-2 p-2.5 rounded bg-caution-bg text-caution-ink text-xs font-semibold border border-caution/30">
            <AlertCircle className="w-4 h-4 shrink-0 text-caution" aria-hidden="true" />
            <span>{pageWarning}</span>
          </div>
        )}
      </div>
    </div>
  );
};
