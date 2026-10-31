import React from 'react';
import { useT } from '../../lib/i18n';

interface PrivacyCubeProps {
  className?: string;
}

export const PrivacyCube: React.FC<PrivacyCubeProps> = ({ className = '' }) => {
  const { t } = useT();

  return (
    <div className={`cubewrap ${className}`} aria-hidden="true">
      <div className="cube">
        <div>
          <span>
            <b>🔒</b>
            <span className="block text-xs sm:text-sm mt-1">{t('nav.localProcessing')}</span>
          </span>
        </div>
        <div>
          <span>
            <b>🗑</b>
            <span className="block text-xs sm:text-sm mt-1">{t('nav.deleteSession')}</span>
          </span>
        </div>
        <div>
          <span>
            <b>🚫</b>
            <span className="block text-xs sm:text-sm mt-1 leading-snug">{t('landing.privacyTitle')}</span>
          </span>
        </div>
        <div>
          <span>
            <b>📖</b>
            <span className="block text-xs sm:text-sm mt-1 leading-snug">{t('disclaimers.banner').split(/[.|।]/)[0].trim()}</span>
          </span>
        </div>
      </div>
    </div>
  );
};

export default PrivacyCube;
