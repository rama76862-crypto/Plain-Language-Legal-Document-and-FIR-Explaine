/**
 * ErrorConflictOverlay Component (P-05)
 * Handles REVISION_CONFLICT (409), MODEL_BUSY (429), Session Expired (404),
 * and Connection Lost (NETWORK_ERROR).
 * Always presents actionable remedies. Never displays raw document text.
 */

import React from 'react';
import { Modal, Button, MonoLabel } from '../design/primitives';
import { AlertCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import type { ErrorCode } from '../lib/types';

export interface ErrorConflictOverlayProps {
  isOpen: boolean;
  errorCode: ErrorCode | string;
  errorMessage: string;
  requestId?: string;
  retryable?: boolean;
  onRetry?: () => void;
  onReload?: () => void;
  onWipe?: () => void;
  onClose?: () => void;
}

export const ErrorConflictOverlay: React.FC<ErrorConflictOverlayProps> = ({
  isOpen,
  errorCode,
  errorMessage,
  requestId,
  retryable,
  onRetry,
  onReload,
  onWipe,
  onClose,
}) => {
  if (!isOpen) return null;

  const isConflict = errorCode === 'REVISION_CONFLICT' || errorCode === '409';
  const isBusy = errorCode === 'MODEL_BUSY' || errorCode === '429';
  const isExpired = errorCode === 'NOT_FOUND' || errorCode === '404';

  const title = isConflict
    ? 'Document Revision Conflict (409)'
    : isBusy
    ? 'Local AI Model Busy (429)'
    : isExpired
    ? 'Document Session Expired (404)'
    : 'System Communication Notice';

  return (
    <Modal isOpen={isOpen} onClose={onClose || (() => {})} title={title} maxWidth="md">
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          {isConflict || isExpired ? (
            <AlertCircle className="w-6 h-6 text-concern shrink-0 mt-0.5" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-caution shrink-0 mt-0.5" />
          )}
          <div className="text-sm text-ink space-y-1">
            <p className="font-semibold">{errorMessage}</p>
            {isConflict && (
              <p className="text-xs text-mute">
                The document was modified in another request. Your view is outdated. Reloading will fetch the latest verified clauses while preserving your local edits for comparison.
              </p>
            )}
            {isBusy && (
              <p className="text-xs text-mute">
                The local GPU model queue is currently processing another clause. Your request can be safely retried without re-entering questions.
              </p>
            )}
            {isExpired && (
              <p className="text-xs text-mute">
                Sessions are temporary and terminate automatically upon inactivity or tab reload.
              </p>
            )}
          </div>
        </div>

        {requestId && (
          <div className="pt-2 border-t border-line flex items-center justify-between">
            <MonoLabel>REQUEST TRACE</MonoLabel>
            <span className="font-mono text-[11px] text-mute">{requestId}</span>
          </div>
        )}

        <div className="flex flex-wrap justify-end gap-2 pt-2 border-t border-line">
          {isConflict && onReload && (
            <Button
              variant="primary"
              size="sm"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={onReload}
            >
              Reload Latest Clauses
            </Button>
          )}

          {retryable && onRetry && (
            <Button
              variant="primary"
              size="sm"
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
              onClick={onRetry}
            >
              Retry Request
            </Button>
          )}

          {isExpired && onWipe && (
            <Button variant="primary" size="sm" onClick={onWipe}>
              Return to Upload
            </Button>
          )}

          {onWipe && !isExpired && (
            <Button variant="danger-outline" size="sm" onClick={onWipe}>
              Wipe Session
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
};
