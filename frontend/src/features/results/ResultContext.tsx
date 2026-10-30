/**
 * ResultContext
 * Manages analysis lifecycle, status polling, output language state,
 * and result caching keyed by (documentId, revision, analysisId, outputLanguage).
 */

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import type {
  ResultObject,
  AnalysisStatus,
  AnalysisProgress,
  OutputLanguage,
  QuestionAnswer,
} from '../../lib/types';
import { createAnalysis, getAnalysis, cancelAnalysis as deleteAnalysis, ApiClientError } from '../../lib/api';

export type ResultTab = 'overview' | 'clauses' | 'attention' | 'dates' | 'legalAid' | 'ask' | 'export' | 'actionPack' | 'compare';

export interface QuestionHistoryEntry {
  id: string;
  question: string;
  clientRequestId: string;
  answer: QuestionAnswer | null;
  error?: { code: string; message: string; retryable: boolean };
  timestamp: number;
}

interface ResultError {
  code: string;
  message: string;
  retryable?: boolean;
}

interface ResultContextValue {
  status: AnalysisStatus | 'idle';
  progress: AnalysisProgress;
  result: ResultObject | null;
  activeTab: ResultTab;
  setActiveTab: (tab: ResultTab) => void;
  outputLanguage: OutputLanguage;
  changeOutputLanguage: (lang: OutputLanguage) => void;
  isAnalyzing: boolean;
  isDimmedLoading: boolean;
  pendingLanguage: OutputLanguage | null;
  error: ResultError | null;
  startAnalysis: (targetLang?: OutputLanguage) => Promise<void>;
  retryAnalysis: () => Promise<void>;
  cancelAnalysis: () => Promise<void>;
  isCancelling: boolean;
  documentType: string;
  analysisId: string | null;
  qaHistory: QuestionHistoryEntry[];
  addQaHistory: (entry: QuestionHistoryEntry) => void;
  updateQaHistory: (id: string, update: Partial<QuestionHistoryEntry>) => void;
  clearQaHistory: () => void;
}

const ResultContext = createContext<ResultContextValue | null>(null);

interface ResultProviderProps {
  documentId: string;
  sessionToken: string;
  revision: number;
  initialOutputLanguage: OutputLanguage;
  documentType?: string;
  onDeleted?: () => void;
  children: React.ReactNode;
}

export const ResultProvider: React.FC<ResultProviderProps> = ({
  documentId,
  sessionToken,
  revision,
  initialOutputLanguage,
  documentType = 'agreement',
  onDeleted,
  children,
}) => {
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>(initialOutputLanguage);
  const [pendingLanguage, setPendingLanguage] = useState<OutputLanguage | null>(null);
  const [status, setStatus] = useState<AnalysisStatus | 'idle'>('idle');
  const [progress, setProgress] = useState<AnalysisProgress>({ completed_clauses: 0, total_clauses: 0 });
  const [result, setResult] = useState<ResultObject | null>(null);
  const [activeTab, setActiveTab] = useState<ResultTab>('overview');
  const [error, setError] = useState<ResultError | null>(null);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);
  const [qaHistory, setQaHistory] = useState<QuestionHistoryEntry[]>([]);
  const historyBinding = [documentId, revision, analysisId, outputLanguage].join(":");
  const currentHistoryBinding = useRef(historyBinding);
  currentHistoryBinding.current = historyBinding;
  useEffect(() => { setQaHistory([]); }, [historyBinding]);

  const addQaHistory = useCallback((entry: QuestionHistoryEntry) => {
    if (currentHistoryBinding.current !== historyBinding) return;
    setQaHistory((prev) => {
      const updated = [...prev.filter(item => item.id !== entry.id), entry];
      if (updated.length > 20) {
        return updated.slice(updated.length - 20);
      }
      return updated;
    });
  }, [historyBinding]);

  const updateQaHistory = useCallback((id: string, update: Partial<QuestionHistoryEntry>) => {
    setQaHistory((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...update } : item))
    );
  }, []);

  const clearQaHistory = useCallback(() => {
    setQaHistory([]);
  }, []);

  // Key tracking to ignore stale responses
  const activeKeyRef = useRef<string>('');
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Clear polling timers
  const clearPollTimer = () => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  // Discard results if revision changes
  const prevRevisionRef = useRef(revision);
  useEffect(() => {
    if (prevRevisionRef.current !== revision) {
      prevRevisionRef.current = revision;
      setResult(null);
      setStatus('idle');
      setProgress({ completed_clauses: 0, total_clauses: 0 });
      setError(null);
      activeKeyRef.current = '';
      abortControllerRef.current?.abort();
      setAnalysisId(null);
      setPendingLanguage(null);
      setQaHistory([]);
      clearPollTimer();
    }
  }, [revision]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      clearPollTimer();
      abortControllerRef.current?.abort();
    };
  }, []);

  const pollAnalysis = useCallback(
    async (targetAnalysisId: string, targetLang: OutputLanguage, key: string, attempt: number = 0) => {
      if (activeKeyRef.current !== key) return;

      abortControllerRef.current?.abort();
      abortControllerRef.current = new AbortController();

      try {
        const data = await getAnalysis(
          documentId,
          targetAnalysisId,
          sessionToken,
          abortControllerRef.current.signal
        );

        if (activeKeyRef.current !== key) return;

        setStatus(data.status);
        setProgress(data.progress);

        if (data.status === 'complete' || data.status === 'needs_review') {
          if (data.result) {
            setResult(data.result);
          }
          setOutputLanguage(targetLang);
          setPendingLanguage(null);
          setError(null);
          clearPollTimer();
        } else if (data.status === 'failed') {
          setError({
            code: 'ANALYSIS_FAILED',
            message: data.warnings?.[0] || 'Analysis failed. Please try again.',
            retryable: true,
          });
          setPendingLanguage(null);
          clearPollTimer();
        } else {
          // Continue polling: queued or running
          const delays = [1500, 2000, 2500, 3000];
          const delay = delays[Math.min(attempt, delays.length - 1)];
          pollTimerRef.current = setTimeout(() => {
            pollAnalysis(targetAnalysisId, targetLang, key, attempt + 1);
          }, delay);
        }
      } catch (err: unknown) {
        if (activeKeyRef.current !== key) return;

        if (err instanceof ApiClientError) {
          if (err.status === 404) {
            setError({ code: 'NOT_FOUND', message: 'Document session expired.' });
            onDeleted?.();
            clearPollTimer();
            return;
          }
          if (err.status === 429) {
            // Model busy - retry with delay
            pollTimerRef.current = setTimeout(() => {
              pollAnalysis(targetAnalysisId, targetLang, key, attempt + 1);
            }, 3000);
            return;
          }
        }

        // Network error backoff
        if (attempt < 5) {
          pollTimerRef.current = setTimeout(() => {
            pollAnalysis(targetAnalysisId, targetLang, key, attempt + 1);
          }, 3000);
        } else {
          setError({
            code: 'CONNECTION_LOST',
            message: 'Connection lost while polling analysis.',
            retryable: true,
          });
          setPendingLanguage(null);
          clearPollTimer();
        }
      }
    },
    [documentId, sessionToken, onDeleted]
  );

  const startAnalysis = useCallback(
    async (targetLang?: OutputLanguage) => {
      const lang = targetLang || outputLanguage;
      setError(null);

      if (!documentId || !sessionToken) return;

      const isSwitchingLanguage = lang !== outputLanguage && result !== null;
      if (isSwitchingLanguage) {
        setPendingLanguage(lang);
      } else {
        setStatus('queued');
      }

      clearPollTimer();
      const currentKey = `${documentId}_r${revision}_${lang}_${Date.now()}`;
      activeKeyRef.current = currentKey;

      try {
        const createRes = await createAnalysis(documentId, sessionToken, {
          expected_revision: revision,
          output_language: lang,
        });

        if (activeKeyRef.current !== currentKey) return;

        setAnalysisId(createRes.analysis_id);
        setStatus(createRes.status);

        if (createRes.status === 'complete' && createRes.analysis_id) {
          // If already complete in cache, fetch it directly
          await pollAnalysis(createRes.analysis_id, lang, currentKey, 0);
        } else {
          pollAnalysis(createRes.analysis_id, lang, currentKey, 0);
        }
      } catch (err: unknown) {
        if (activeKeyRef.current !== currentKey) return;
        setPendingLanguage(null);
        setStatus('failed');

        if (err instanceof ApiClientError) {
          if (err.status === 404) {
            setError({ code: 'NOT_FOUND', message: 'Session expired.' });
            onDeleted?.();
            return;
          }
          if (err.status === 409) {
            setError({
              code: 'REVISION_CONFLICT',
              message: 'Document revision conflict. Please re-confirm review.',
              retryable: false,
            });
            return;
          }
          if (err.status === 429) {
            setError({
              code: 'MODEL_BUSY',
              message: 'AI processor is currently busy with another task.',
              retryable: true,
            });
            return;
          }
          if (err.code === 'MODEL_UNAVAILABLE') {
            setError({
              code: 'MODEL_UNAVAILABLE',
              message: 'AI explanation service is unavailable. Extraction and review still work.',
              retryable: true,
            });
            return;
          }
        }

        setError({
          code: 'NETWORK_ERROR',
          message: 'Unable to communicate with the analysis service. Please retry.',
          retryable: true,
        });
      }
    },
    [
      outputLanguage,
      documentId,
      sessionToken,
      revision,
      result,
      documentType,
      pollAnalysis,
      onDeleted,
    ]
  );

  const retryAnalysis = useCallback(async () => {
    await startAnalysis(pendingLanguage || outputLanguage);
  }, [startAnalysis, pendingLanguage, outputLanguage]);

  const changeOutputLanguage = useCallback(
    (lang: OutputLanguage) => {
      if (lang === outputLanguage && !pendingLanguage) return;
      startAnalysis(lang);
    },
    [outputLanguage, pendingLanguage, startAnalysis]
  );

  const cancelCurrentAnalysis=useCallback(async () => {
    if (!analysisId || isCancelling) return;
    const key=activeKeyRef.current;
    setIsCancelling(true);
    activeKeyRef.current='';
    clearPollTimer();
    abortControllerRef.current?.abort();
    try {
      await deleteAnalysis(documentId,sessionToken,analysisId);
      const retained=result && result.analysis_id!==analysisId ? result : null;
      setResult(retained);
      setStatus(retained?'needs_review':'idle');
      setAnalysisId(retained?.analysis_id??null);
      if(retained) setOutputLanguage(retained.output_language);
      setPendingLanguage(null);
      setProgress({completed_clauses:0,total_clauses:0});
      setError(null);
    } catch (error) {
      setError({code:error instanceof ApiClientError?error.code:'NETWORK_ERROR',message:error instanceof Error?error.message:'Cancellation was not confirmed.',retryable:false});
      activeKeyRef.current=key;
      if(key) void pollAnalysis(analysisId,pendingLanguage||outputLanguage,key);
    } finally {setIsCancelling(false);}
  },[analysisId,isCancelling,documentId,sessionToken,result,pendingLanguage,outputLanguage,pollAnalysis]);

  const isAnalyzing = status === 'queued' || status === 'running';
  const isDimmedLoading = pendingLanguage !== null;

  // Auto-start analysis on mount when arriving from review confirmation
  const hasAutoStarted = useRef(false);
  useEffect(() => {
    let disposed=false;
    queueMicrotask(() => {
      if (!disposed && status === 'idle' && !hasAutoStarted.current && documentId && sessionToken) {
        hasAutoStarted.current = true;
        void startAnalysis();
      }
    });
    return () => {disposed=true;};
  }, [status, startAnalysis, documentId, sessionToken]);

  return (
    <ResultContext.Provider
      value={{
        status,
        progress,
        result,
        activeTab,
        setActiveTab,
        outputLanguage,
        changeOutputLanguage,
        isAnalyzing,
        isDimmedLoading,
        pendingLanguage,
        error,
        startAnalysis,
        retryAnalysis,
        cancelAnalysis:cancelCurrentAnalysis,
        isCancelling,
        documentType: result?.document_type ?? documentType,
        analysisId,
        qaHistory,
        addQaHistory,
        updateQaHistory,
        clearQaHistory,
      }}
    >
      {children}
    </ResultContext.Provider>
  );
};

export const useResult = (): ResultContextValue => {
  const context = useContext(ResultContext);
  if (!context) {
    throw new Error('useResult must be used within a ResultProvider');
  }
  return context;
};
