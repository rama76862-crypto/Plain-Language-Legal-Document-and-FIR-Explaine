/**
 * LanguageDocTypeSelector Component (C-04)
 * Independent controls for:
 * 1. Document Input Language (auto, en, hi, pa)
 * 2. Target Explanation Language (en, hi, pa)
 * 3. Document Classification Type (auto, agreement, fir, notice, other)
 * Displays capability badge based on health telemetry.
 */

import React from 'react';
import type { InputLanguage, OutputLanguage, InputDocumentType, HealthResponse } from '../../lib/types';
import { Select } from '../../design/primitives';
import { useT } from '../../lib/i18n';
import { HelpCircle } from 'lucide-react';

interface LanguageDocTypeSelectorProps {
  inputLanguage: InputLanguage;
  outputLanguage: OutputLanguage;
  documentType: InputDocumentType;
  healthData?: HealthResponse | null;
  onChangeInputLanguage: (lang: InputLanguage) => void;
  onChangeOutputLanguage: (lang: OutputLanguage) => void;
  onChangeDocumentType: (type: InputDocumentType) => void;
  disabled?: boolean;
}

export const LanguageDocTypeSelector: React.FC<LanguageDocTypeSelectorProps> = ({
  inputLanguage,
  outputLanguage,
  documentType,
  onChangeInputLanguage,
  onChangeOutputLanguage,
  onChangeDocumentType,
  disabled = false,
}) => {
  const { t } = useT();

  const inputLangOptions = [
    { value: 'auto', label: `${t('languages.auto')} (Detect)` },
    { value: 'en', label: `${t('languages.en')} [Review required]` },
    { value: 'hi', label: `${t('languages.hi')} [Experimental]` },
    { value: 'pa', label: `${t('languages.pa')} [Experimental]` },
  ];

  const outputLangOptions = [
    { value: 'en', label: `${t('languages.en')} [Default · Review required]` },
    { value: 'hi', label: `${t('languages.hi')} [Experimental]` },
    { value: 'pa', label: `${t('languages.pa')} [Experimental]` },
  ];

  const docTypeOptions = [
    { value: 'auto', label: `${t('docTypes.auto')} (Auto-route)` },
    { value: 'agreement', label: t('docTypes.agreement') },
    { value: 'fir', label: t('docTypes.fir') },
    { value: 'notice', label: t('docTypes.notice') },
    { value: 'other', label: t('docTypes.other') },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* 1. Document Language */}
        <Select
          label={t('upload.docLanguageLabel')}
          value={inputLanguage}
          onChange={(val) => onChangeInputLanguage(val as InputLanguage)}
          options={inputLangOptions}
          disabled={disabled}
        />

        {/* 2. Target Explanation Language */}
        <Select
          label={t('upload.explainInLabel')}
          value={outputLanguage}
          onChange={(val) => onChangeOutputLanguage(val as OutputLanguage)}
          options={outputLangOptions}
          disabled={disabled}
        />

        {/* 3. Document Category */}
        <Select
          label={t('upload.docTypeLabel')}
          value={documentType}
          onChange={(val) => onChangeDocumentType(val as InputDocumentType)}
          options={docTypeOptions}
          disabled={disabled}
        />
      </div>

      {/* Helper text clarifying translation behavior */}
      <div className="flex items-start gap-2 p-2.5 bg-bg2/60 rounded border border-line text-xs text-mute">
        <HelpCircle className="w-4 h-4 text-blue shrink-0 mt-0.5" aria-hidden="true" />
        <p>{t('upload.langHelper')}</p>
      </div>
    </div>
  );
};
