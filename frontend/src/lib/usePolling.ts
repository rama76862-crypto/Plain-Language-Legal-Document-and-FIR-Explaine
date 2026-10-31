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

const DEFAULT_BACKOFF = [1500, 3000, 5000];

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
    backoff = DEFAULT_BACKOFF,
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
  const generationRef = useRef(0);
  // Inline callbacks change on each render; they must not restart the request loop.
  const callbacksRef = useRef({ shouldStop, onSuccess, onError, backoff });
  callbacksRef.current = { shouldStop, onSuccess, onError, backoff };

  const stop = useCallback(() => {
    isStoppedRef.current = true;
    generationRef.current += 1;
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
    const generation = generationRef.current;
    abortControllerRef.current = ac;

    try {
      const data = await pollFn(ac.signal);
      if (ac.signal.aborted || isStoppedRef.current || generation !== generationRef.current) return;

      // Successful request resets failure count
      failureCountRef.current = 0;
      setConnectionLost(false);
      callbacksRef.current.onSuccess?.(data);

      if (callbacksRef.current.shouldStop(data)) {
        stop();
        return;
      }

      // Schedule next tick
      if (!isStoppedRef.current) {
        timeoutIdRef.current = setTimeout(tick, intervalMs);
      }
    } catch (err: unknown) {
      if (ac.signal.aborted || isStoppedRef.current || generation !== generationRef.current) return;

      failureCountRef.current += 1;
      callbacksRef.current.onError?.(err);
      if (isStoppedRef.current) return;
      const delays = callbacksRef.current.backoff;

      if (failureCountRef.current >= delays.length) {
        // Exceeded maximum backoff tries -> pause and notify UI
        setConnectionLost(true);
        setIsPolling(false);
        return;
      }

      const nextDelay = delays[failureCountRef.current - 1] || delays[delays.length - 1];
      if (!isStoppedRef.current) {
        timeoutIdRef.current = setTimeout(tick, nextDelay);
      }
    }
  }, [pollFn, intervalMs, stop]);

  const retry = useCallback(() => {
    stop();
    isStoppedRef.current = false;
    failureCountRef.current = 0;
    setConnectionLost(false);
    setIsPolling(true);
    tick();
  }, [tick, stop]);

  useEffect(() => {
    if (enabled) {
      isStoppedRef.current = false;
      failureCountRef.current = 0;
      setConnectionLost(false);
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
