/**
 * NyayaSarathi In-Memory Session Context
 * 
 * HARD RULE VERIFICATION:
 * - Session token, document IDs, clause texts, and Blob URLs are held EXCLUSIVELY in React memory.
 * - ZERO usage of localStorage, sessionStorage, cookies, IndexedDB, or service-worker caches.
 * - When browser tab refreshes or unmounts, all session credentials are permanently lost.
 * - On session reset or termination, Blob URLs are explicitly revoked via URL.revokeObjectURL().
 */

import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react';
import type { DocumentStatus, DocumentType, Language, OutputLanguage } from './types';
import { config } from './config';
import { deleteDocument, getDocument, ApiClientError } from './api';

interface SessionState {
  documentId: string | null;
  sessionToken: string | null;
  revision: number;
  documentStatus: DocumentStatus | null;
  filename: string | null;
  inputLanguage: Language;
  outputLanguage: OutputLanguage;
  documentType: DocumentType;
  selectedClauseId: string | null;
  sourceBlobUrl: string | null;
  inactivityRemainingSeconds: number;
  serverExpiresAt: string | null;
  warnings: string[];
  reviewConfirmed: boolean;
}

interface SessionContextType extends SessionState {
  startSession: (params: {
    documentId: string;
    sessionToken: string;
    revision: number;
    filename: string;
    inputLanguage: Language;
    outputLanguage: OutputLanguage;
    documentType: DocumentType;
    expiresAt?: string | null;
  }) => void;
  setDocumentStatus: (status: DocumentStatus) => void;
  setRevision: (revision: number) => void;
  setSourceBlobUrl: (url: string | null) => void;
  selectClause: (clauseId: string | null) => void;
  setOutputLanguage: (lang: OutputLanguage) => void;
  setDocumentType: (docType: DocumentType) => void;
  setInputLanguage: (inputLang: Language) => void;
  setReviewConfirmed: (confirmed: boolean) => void;
  setWarnings: (warnings: string[]) => void;
  setServerExpiresAt: (expiresAt: string | null) => void;
  resetInactivityTimer: () => void;
  resetSession: (callServerDelete?: boolean) => Promise<boolean>;
  getAbortSignal: () => AbortSignal;
}

const SessionContext = createContext<SessionContextType | null>(null);

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [revision, setRevisionState] = useState<number>(1);
  const [documentStatus, setDocumentStatus] = useState<DocumentStatus | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [inputLanguage, setInputLanguage] = useState<Language>('en');
  const [outputLanguage, setOutputLanguage] = useState<OutputLanguage>('en');
  const [documentType, setDocumentType] = useState<DocumentType>('agreement');
  const [selectedClauseId, setSelectedClauseId] = useState<string | null>(null);
  const [sourceBlobUrl, setSourceBlobUrlState] = useState<string | null>(null);
  const [serverExpiresAt, setServerExpiresAtState] = useState<string | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [reviewConfirmed, setReviewConfirmed] = useState<boolean>(false);

  const initialTimeoutSecs = config.inactivityTimeoutMinutes * 60;
  const [inactivityRemainingSeconds, setInactivityRemainingSeconds] = useState<number>(initialTimeoutSecs);

  // Shared AbortController for in-flight queries
  const abortControllerRef = useRef<AbortController>(new AbortController());

  const getAbortSignal = useCallback(() => {
    return abortControllerRef.current.signal;
  }, []);

  const resetInactivityTimer = useCallback(() => {
    setInactivityRemainingSeconds(config.inactivityTimeoutMinutes * 60);
  }, []);

  const setServerExpiresAt = useCallback((expiresAt: string | null) => {
    setServerExpiresAtState(expiresAt);
    if (expiresAt) {
      const serverSecs = Math.max(0, Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000));
      setInactivityRemainingSeconds(serverSecs);
    }
  }, []);

  const setSourceBlobUrl = useCallback((newUrl: string | null) => {
    setSourceBlobUrlState((prevUrl) => {
      if (prevUrl && prevUrl !== newUrl) {
        URL.revokeObjectURL(prevUrl);
      }
      return newUrl;
    });
  }, []);

  const startSession = useCallback(
    (params: {
      documentId: string;
      sessionToken: string;
      revision: number;
      filename: string;
      inputLanguage: Language;
      outputLanguage: OutputLanguage;
      documentType: DocumentType;
      expiresAt?: string | null;
    }) => {
      setDocumentId(params.documentId);
      setSessionToken(params.sessionToken);
      setRevisionState(params.revision);
      setFilename(params.filename);
      setInputLanguage(params.inputLanguage);
      setOutputLanguage(params.outputLanguage);
      setDocumentType(params.documentType);
      setDocumentStatus('extracting');
      setReviewConfirmed(false);
      setWarnings([]);
      setSelectedClauseId(null);
      if (params.expiresAt) {
        setServerExpiresAt(params.expiresAt);
      } else {
        resetInactivityTimer();
      }
    },
    [resetInactivityTimer, setServerExpiresAt]
  );

  const setRevision = useCallback((rev: number) => {
    setRevisionState(rev);
  }, []);

  const selectClause = useCallback((clauseId: string | null) => {
    setSelectedClauseId(clauseId);
  }, []);

  const resetSession = useCallback(
    async (callServerDelete: boolean = true) => {
      let serverDeletionConfirmed = true;
      // 1. Abort any active network requests
      abortControllerRef.current.abort();
      abortControllerRef.current = new AbortController();

      // 2. Call server DELETE if session exists and requested
      if (callServerDelete && documentId && sessionToken) {
        try {
          await deleteDocument(documentId, sessionToken);
        } catch {
          serverDeletionConfirmed = false;
        }
      }

      // 3. Revoke Blob URL if allocated
      if (sourceBlobUrl) {
        URL.revokeObjectURL(sourceBlobUrl);
      }

      // 4. Wipe all React state to default
      setDocumentId(null);
      setSessionToken(null);
      setRevisionState(1);
      setDocumentStatus(null);
      setFilename(null);
      setInputLanguage('en');
      setOutputLanguage('en');
      setDocumentType('agreement');
      setSelectedClauseId(null);
      setSourceBlobUrlState(null);
      setServerExpiresAtState(null);
      setWarnings([]);
      setReviewConfirmed(false);
      resetInactivityTimer();
      return serverDeletionConfirmed;
    },
    [documentId, sessionToken, sourceBlobUrl, resetInactivityTimer]
  );

  // Review, questions and analysis can extend retention on the server. Read the
  // actual deadline without extending it so an active session is not wiped early.
  useEffect(() => {
    if (!documentId || !sessionToken) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const syncExpiry = async () => {
      try {
        const doc = await getDocument(documentId, sessionToken, controller.signal);
        if (!controller.signal.aborted && doc.expires_at) setServerExpiresAt(doc.expires_at);
      } catch (error) {
        if (!controller.signal.aborted && error instanceof ApiClientError && error.status === 404) {
          await resetSession(false);
          return;
        }
      }
      if (!controller.signal.aborted) timer = setTimeout(syncExpiry, 15000);
    };
    void syncExpiry();
    return () => { controller.abort(); clearTimeout(timer); };
  }, [documentId, sessionToken, setServerExpiresAt, resetSession]);

  // Inactivity countdown ticker synchronized with server expires_at
  useEffect(() => {
    if (!documentId) return;

    const interval = setInterval(() => {
      setInactivityRemainingSeconds((prev) => {
        if (serverExpiresAt) {
          const serverSecs = Math.max(0, Math.floor((new Date(serverExpiresAt).getTime() - Date.now()) / 1000));
          return serverSecs;
        }

        if (prev <= 1) {
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [documentId, serverExpiresAt, resetSession]);

  useEffect(() => {
    if (!documentId || !sessionToken || inactivityRemainingSeconds > 0) return;
    const controller = new AbortController();
    // Recheck before deleting: a user request may just have extended the server TTL.
    void getDocument(documentId, sessionToken, controller.signal).then(doc => {
      if (!controller.signal.aborted && doc.expires_at) setServerExpiresAt(doc.expires_at);
    }).catch(() => {
      if (!controller.signal.aborted) void resetSession(true);
    });
    return () => controller.abort();
  }, [documentId, sessionToken, inactivityRemainingSeconds, setServerExpiresAt, resetSession]);

  // Only reset local timer on activity if no authoritative server expiry is bound
  useEffect(() => {
    if (!documentId || serverExpiresAt) return;

    const onUserActivity = () => {
      resetInactivityTimer();
    };

    window.addEventListener('pointerdown', onUserActivity);
    window.addEventListener('keydown', onUserActivity);

    return () => {
      window.removeEventListener('pointerdown', onUserActivity);
      window.removeEventListener('keydown', onUserActivity);
    };
  }, [documentId, serverExpiresAt, resetInactivityTimer]);

  // Cleanup Blob URLs on unmount
  useEffect(() => {
    return () => {
      if (sourceBlobUrl) {
        URL.revokeObjectURL(sourceBlobUrl);
      }
    };
  }, [sourceBlobUrl]);

  return (
    <SessionContext.Provider
      value={{
        documentId,
        sessionToken,
        revision,
        documentStatus,
        filename,
        inputLanguage,
        outputLanguage,
        documentType,
        selectedClauseId,
        sourceBlobUrl,
        inactivityRemainingSeconds,
        serverExpiresAt,
        warnings,
        reviewConfirmed,
        startSession,
        setDocumentStatus,
        setRevision,
        setSourceBlobUrl,
        selectClause,
        setOutputLanguage,
        setDocumentType,
        setInputLanguage,
        setReviewConfirmed,
        setWarnings,
        setServerExpiresAt,
        resetInactivityTimer,
        resetSession,
        getAbortSignal,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};

export function useSession(): SessionContextType {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}
