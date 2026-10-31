import { useEffect, useState } from "react";
import { getCapabilities } from "../lib/api";
import { useT } from "../lib/i18n";

export function ProcessingDisclosure() {
  const { t } = useT();
  const [hosted, setHosted] = useState(false);

  useEffect(() => {
    const c = new AbortController();
    getCapabilities(c.signal)
      .then((v) => setHosted(v.processing?.external_ai_inference === true))
      .catch(() => {});
    return () => c.abort();
  }, []);

  return hosted ? (
    <div
      role="note"
      className="border-b border-amber-300 bg-amber-50 px-5 py-3 text-xs text-amber-950"
    >
      {t('disclosures.hostedMode')}
    </div>
  ) : null;
}
