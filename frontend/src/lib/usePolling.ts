/**
 * usePolling Hook
 * Robust, production-grade asynchronous polling:
 * - Uses recursive setTimeout (never setInterval) to prevent overlapping requests
 * - Issues a fresh AbortController per tick
 * - Handles backoff on consecutive network failures (1.5s -> 3s -> 5s)
 * - Exposes connectionLost flag and manual retry trigger
 * - Automatically cancels on unmount, terminal status, or manual stop
 */

import { useState, useRef, useEffect, useCallback } from 'react';

interface PollingOptions<T> {
  intervalMs?: number;
  backoff?: number[];
  shouldStop: (data: T) => boolean;
  onSuccess?: (data: T) => void;
  onError?: (err: unknown) => void;
  enabled?: boolean;
}

export function usePolling<T>(
  pollFn: (signal: AbortSignal) => Promise<T>,
  options: PollingOptions<T>
) {
  const {
    intervalMs = 1500,
    backoff = [1500, 3000, 5000],
    shouldStop,
    onSuccess,
    onError,
    enabled = true,
  } = options;

  const [isPolling, setIsPolling] = useState(enabled);
  const [connectionLost, setConnectionLost] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const timeoutIdRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const failureCountRef = useRef<number>(0);
  const isStoppedRef = useRef<boolean>(!enabled);

  const stop = useCallback(() => {
    isStoppedRef.current = true;
    setIsPolling(false);
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (timeoutIdRef.current) {
      clearTimeout(timeoutIdRef.current);
      timeoutIdRef.current = null;
    }
  }, []);

  const tick = useCallback(async () => {
    if (isStoppedRef.current) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const ac = new AbortController();
    abortControllerRef.current = ac;

    try {
      const data = await pollFn(ac.signal);

      // Successful request resets failure count
      failureCountRef.current = 0;
      setConnectionLost(false);
      onSuccess?.(data);

      if (shouldStop(data)) {
        stop();
        return;
      }

      // Schedule next tick
      if (!isStoppedRef.current) {
        timeoutIdRef.current = setTimeout(tick, intervalMs);
      }
    } catch (err: unknown) {
      if (ac.signal.aborted) return;

      failureCountRef.current += 1;
      onError?.(err);

      if (failureCountRef.current >= backoff.length) {
        // Exceeded maximum backoff tries -> pause and notify UI
        setConnectionLost(true);
        setIsPolling(false);
        return;
      }

      const nextDelay = backoff[failureCountRef.current - 1] || backoff[backoff.length - 1];
      if (!isStoppedRef.current) {
        timeoutIdRef.current = setTimeout(tick, nextDelay);
      }
    }
  }, [pollFn, intervalMs, backoff, shouldStop, onSuccess, onError, stop]);

  const retry = useCallback(() => {
    isStoppedRef.current = false;
    failureCountRef.current = 0;
    setConnectionLost(false);
    setIsPolling(true);
    tick();
  }, [tick]);

  useEffect(() => {
    if (enabled) {
      isStoppedRef.current = false;
      setIsPolling(true);
      tick();
    } else {
      stop();
    }

    return () => {
      stop();
    };
  }, [enabled, tick, stop]);

  return {
    isPolling,
    connectionLost,
    retry,
    stop,
  };
}
