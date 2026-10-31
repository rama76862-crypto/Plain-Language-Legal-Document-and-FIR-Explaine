/**
 * DeleteSessionDialog Component
 * Manages explicit user request to terminate session and destroy data.
 * Executes single DELETE request, revokes Blob URLs, renders particle dissolve,
 * wipes volatile state, and navigates home.
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Modal, Button } from '../design/primitives';
import { useSession } from '../lib/session';
import { useT } from '../lib/i18n';
import { useToast } from '../design/primitives';
import { ShredDissolve } from '../design/scenes/ShredDissolve';
import { Trash2 } from 'lucide-react';

export const DeleteSessionDialog: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const { resetSession } = useSession();
  const { t } = useT();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [isDeleting, setIsDeleting] = useState(false);
  const [showShred, setShowShred] = useState(false);

  const handleConfirm = async () => {
    setIsDeleting(true);
    setShowShred(true);

    try {
      const deletePromise = resetSession(true);
      // Let the particle dissolution animation play so user sees physical erasure feedback
      const [confirmed] = await Promise.all([
        deletePromise,
        new Promise((resolve) => setTimeout(resolve, 1100)),
      ]);
      showToast(
        confirmed ? t('privacy.sessionDeletedToast') : t('privacy.serverUnconfirmedToast'),
        confirmed ? 'info' : 'warn'
      );
    } catch {
      showToast(t('privacy.serverUnconfirmedToast'), 'warn');
    } finally {
      setIsDeleting(false);
      setShowShred(false);
      onClose();
      navigate('/');
    }
  };

  return (
    <>
      <Modal
        isOpen={isOpen && !showShred}
        onClose={onClose}
        title={t('privacy.dialogTitle')}
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            <Trash2 className="w-5 h-5 text-concern shrink-0 mt-0.5" />
            <p className="text-sm text-ink">{t('privacy.dialogBody')}</p>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-line">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={isDeleting}>
              {t('privacy.cancel')}
            </Button>
            <Button
              variant="danger-outline"
              size="sm"
              isLoading={isDeleting}
              onClick={handleConfirm}
            >
              {t('privacy.confirmDelete')}
            </Button>
          </div>
        </div>
      </Modal>

      {showShred && <ShredDissolve onDone={() => setShowShred(false)} />}
    </>
  );
};
