/**
 * NotFoundPage Component (404)
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, GlassCard, MonoLabel } from '../design/primitives';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <main className="min-h-[70vh] flex items-center justify-center p-6 text-center">
      <GlassCard className="max-w-md w-full space-y-4 p-8">
        <MonoLabel>ERROR 404</MonoLabel>
        <h1 className="text-2xl font-bold text-navy">Page Not Found</h1>
        <p className="text-sm text-mute">
          The requested route does not exist. All active document sessions are accessed through the primary workspace.
        </p>
        <div className="pt-2">
          <Button variant="primary" size="sm" onClick={() => navigate('/')}>
            Return to Home
          </Button>
        </div>
      </GlassCard>
    </main>
  );
};
