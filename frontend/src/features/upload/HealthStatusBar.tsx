/**
 * HealthStatusBar Component (C-02)
 * Telemetry on local backend readiness:
 * - Checks extraction engine and local LLM generator status
 * - Displays available OCR languages and tested language capability matrix (3x3)
 * - Exposes offline state to guard upload actions
 */

import React, { useEffect, useState, useCallback } from 'react';
import { getHealth } from '../../lib/api';
import type { HealthResponse } from '../../lib/types';
import { Banner, Button, Skeleton, MonoLabel } from '../../design/primitives';
import { CheckCircle2, WifiOff, RefreshCw } from 'lucide-react';

interface HealthStatusBarProps {
  onHealthStatusChange?: (isHealthy: boolean, healthData: HealthResponse | null) => void;
}

export const HealthStatusBar: React.FC<HealthStatusBarProps> = ({
  onHealthStatusChange,
}) => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [offline, setOffline] = useState<boolean>(false);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setOffline(false);

    try {
      const data = await getHealth();
      setHealth(data);
      onHealthStatusChange?.(data.extraction_ready, data);
    } catch {
      setOffline(true);
      setHealth(null);
      onHealthStatusChange?.(false, null);
    } finally {
      setLoading(false);
    }
  }, [onHealthStatusChange]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  if (loading) {
    return (
      <div className="w-full flex items-center justify-between p-3 bg-paper/60 border border-line rounded-md text-xs font-mono">
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-4 w-32" />
      </div>
    );
  }

  if (offline) {
    return (
      <Banner
        variant="error"
        title="Local API Server Offline"
        action={{ label: 'Retry connection', onClick: fetchStatus }}
        className="w-full"
      >
        <div className="flex items-center gap-2">
          <WifiOff className="w-4 h-4 text-concern" aria-hidden="true" />
          <span>Backend connection offline. Uploads are currently unavailable.</span>
        </div>
      </Banner>
    );
  }

  const isPartial = health && health.extraction_ready && !health.model_ready;

  return (
    <div className="w-full space-y-2">
      {isPartial && (
        <Banner variant="warn" title="AI Model Unavailable or Not Ready">
          Document extraction &amp; review are available. Check the local model service before analysis.
        </Banner>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-paper/70 border border-line rounded-md text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-ok-ink font-semibold">
            <CheckCircle2 className="w-4 h-4 text-ok" aria-hidden="true" />
            <span>Local API Online</span>
          </div>
          <span className="text-line">|</span>
          <div className="flex items-center gap-1 text-mute font-mono">
            <span>OCR:</span>
            <span className="font-bold text-navy">
              {health?.ocr_languages?.join(', ') || 'Not available'}
            </span>
          </div>
        </div>

        {/* 3x3 Matrix Trigger / Summary */}
        <div className="flex items-center gap-2">
          <MonoLabel>LANGUAGE REVIEW:</MonoLabel>
          <div className="flex items-center gap-1 font-mono text-[11px] font-bold text-navy bg-bg2 px-2 py-0.5 rounded">
            <span>{'EN · HI · PA — review pending'}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchStatus} aria-label="Refresh system health">
            <RefreshCw className="w-3.5 h-3.5 text-mute" />
          </Button>
        </div>
      </div>
    </div>
  );
};
