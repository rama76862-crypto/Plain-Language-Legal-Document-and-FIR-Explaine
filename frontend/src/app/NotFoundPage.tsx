/**
 * NotFoundPage Component (404)
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, GlassCard, MonoLabel } from '../design/primitives';
import { useT } from '../lib/i18n';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useT();

  return (
    <main className="min-h-[70vh] flex items-center justify-center p-6 text-center">
      <GlassCard className="max-w-md w-full space-y-4 p-8">
        <MonoLabel>ERROR 404</MonoLabel>
        <h1 className="text-2xl font-bold text-navy">{t('notFound.title')}</h1>
        <p className="text-sm text-mute">
          {t('notFound.description')}
        </p>
        <div className="pt-2">
          <Button variant="primary" size="sm" onClick={() => navigate('/')}>
            {t('notFound.returnHome')}
          </Button>
        </div>
      </GlassCard>
    </main>
  );
};
