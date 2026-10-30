/**
 * Typed i18n Dictionary and useT() Hook
 * Supports nested keys and dynamic {param} interpolation.
 * UI language state is maintained strictly in memory (default: 'en').
 */

import React, { createContext, useContext, useState, useMemo, useCallback } from 'react';
import { en } from '../locales/en';
import { hi } from '../locales/hi';
import { pa } from '../locales/pa';
import type { OutputLanguage } from './types';

export type UILanguage = OutputLanguage;

export type TranslationDictionary = typeof en;

const dictionaries: Record<UILanguage, TranslationDictionary> = {
  en,
  hi,
  pa,
};

interface I18nContextType {
  uiLanguage: UILanguage;
  setUiLanguage: (lang: UILanguage) => void;
  t: (path: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [uiLanguage, setUiLanguage] = useState<UILanguage>('en');

  const dict = useMemo(() => {
    return dictionaries[uiLanguage] || en;
  }, [uiLanguage]);

  const t = useCallback(
    (path: string, params?: Record<string, string | number>): string => {
      const keys = path.split('.');
      let current: unknown = dict;

      for (const key of keys) {
        if (current && typeof current === 'object' && key in current) {
          current = (current as Record<string, unknown>)[key];
        } else {
          // Fallback to English dictionary
          let fallback: unknown = en;
          for (const fbKey of keys) {
            if (fallback && typeof fallback === 'object' && fbKey in fallback) {
              fallback = (fallback as Record<string, unknown>)[fbKey];
            } else {
              return path;
            }
          }
          current = fallback;
          break;
        }
      }

      if (typeof current !== 'string') {
        return path;
      }

      if (!params) {
        return current;
      }

      let interpolated = current;
      for (const [paramKey, paramVal] of Object.entries(params)) {
        interpolated = interpolated.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramVal));
      }

      return interpolated;
    },
    [dict]
  );

  return (
    <I18nContext.Provider value={{ uiLanguage, setUiLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
};

export function useT() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error('useT must be used within an I18nProvider');
  }
  return ctx;
}
