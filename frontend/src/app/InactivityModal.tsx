/**
 * InactivityModal Component (P-06)
 * Disclosed 30-minute retention watchdog.
 * Displays countdown modal when <= 120 seconds remain.
 * Extends session via heartbeat or triggers immediate privacy wiping.
 */

import React from 'react';
import { Modal, Button } from '../design/primitives';
import { useSession } from '../lib/session';
import { keepDocumentAlive } from '../lib/api';
import { useT } from '../lib/i18n';
import { ShieldAlert } from 'lucide-react';

export const InactivityModal: React.FC = () => {
  const {
    documentId,
    sessionToken,
    inactivityRemainingSeconds,
    setServerExpiresAt,
    resetSession,
  } = useSession();
  const { t } = useT();

  // Show modal only when session exists and remaining time <= 120s
  const isExpiring = Boolean(documentId && inactivityRemainingSeconds <= 120 && inactivityRemainingSeconds > 0);

  const handleExtend = async () => {
    if (documentId && sessionToken) {
      try {
        // Authenticated request to server extends TTL and returns new expires_at
        const doc = await keepDocumentAlive(documentId, sessionToken);
        if (doc.expires_at) {
          setServerExpiresAt(doc.expires_at);
        }
      } catch {
        // Ignored
      }
    }
  };

  const handleWipeNow = async () => {
    await resetSession(true);
  };

  return (
    <Modal
      isOpen={isExpiring}
      onClose={() => {}}
      title={t('privacy.modalExpiringTitle')}
      maxWidth="md"
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <ShieldAlert className="w-6 h-6 text-caution shrink-0 mt-1" />
          <div className="space-y-1 text-sm text-ink">
            <p>
              {t('privacy.modalExpiringBody', { seconds: inactivityRemainingSeconds })}
            </p>
            <p className="text-xs text-mute">
              {t('privacy.localTimerNote')}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-line">
          <Button variant="ghost" size="sm" onClick={handleWipeNow}>
            {t('privacy.wipeNowButton')}
          </Button>
          <Button variant="primary" size="sm" onClick={handleExtend}>
            {t('privacy.extendButton')}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
