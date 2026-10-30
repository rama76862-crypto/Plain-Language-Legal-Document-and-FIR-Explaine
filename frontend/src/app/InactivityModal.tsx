/**
 * InactivityModal Component (P-06)
 * Disclosed 30-minute retention watchdog.
 * Displays countdown modal when <= 120 seconds remain.
 * Extends session via heartbeat or triggers immediate privacy wiping.
 */

import React from 'react';
import { Modal, Button, NumberTicker } from '../design/primitives';
import { useSession } from '../lib/session';
import { getDocument } from '../lib/api';
import { useT } from '../lib/i18n';
import { ShieldAlert } from 'lucide-react';

export const InactivityModal: React.FC = () => {
  const {
    documentId,
    sessionToken,
    inactivityRemainingSeconds,
    resetInactivityTimer,
    resetSession,
  } = useSession();
  const { t } = useT();

  // Show modal only when session exists and remaining time <= 120s
  const isExpiring = Boolean(documentId && inactivityRemainingSeconds <= 120 && inactivityRemainingSeconds > 0);

  const handleExtend = async () => {
    resetInactivityTimer();
    if (documentId && sessionToken) {
      try {
        // Send heartbeat request to server to extend TTL
        await getDocument(documentId, sessionToken);
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
              Your session will terminate in{' '}
              <NumberTicker
                value={inactivityRemainingSeconds}
                className="text-base text-concern font-bold"
              />{' '}
              seconds due to inactivity.
            </p>
            <p className="text-xs text-mute">
              This is a local inactivity timer. Clearing the session requests server deletion; temporary server data also has its own expiry policy. Exported copies remain on your device.
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
