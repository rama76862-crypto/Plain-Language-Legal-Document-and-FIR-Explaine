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
import { deleteDocument } from './api';

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
      resetInactivityTimer();
    },
    [resetInactivityTimer]
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
      setWarnings([]);
      setReviewConfirmed(false);
      resetInactivityTimer();
      return serverDeletionConfirmed;
    },
    [documentId, sessionToken, sourceBlobUrl, resetInactivityTimer]
  );

  // Inactivity countdown ticker
  useEffect(() => {
    if (!documentId) return;

    const interval = setInterval(() => {
      setInactivityRemainingSeconds((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          resetSession(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [documentId, resetSession]);

  // Global user interaction listener to reset inactivity timer
  useEffect(() => {
    if (!documentId) return;

    const onUserActivity = () => {
      resetInactivityTimer();
    };

    window.addEventListener('pointerdown', onUserActivity);
    window.addEventListener('keydown', onUserActivity);
    window.addEventListener('scroll', onUserActivity);

    return () => {
      window.removeEventListener('pointerdown', onUserActivity);
      window.removeEventListener('keydown', onUserActivity);
      window.removeEventListener('scroll', onUserActivity);
    };
  }, [documentId, resetInactivityTimer]);

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
