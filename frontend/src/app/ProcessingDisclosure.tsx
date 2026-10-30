import { useEffect, useState } from "react";
import { config } from "../lib/config";
export function ProcessingDisclosure() {
  const [hosted, setHosted] = useState(false);
  useEffect(() => {
    const c = new AbortController();
    fetch(`${config.apiBaseUrl}/capabilities`, {
      signal: c.signal,
      cache: "no-store",
    })
      .then((r) => r.json())
      .then((v) => setHosted(v.processing?.external_ai_inference === true))
      .catch(() => {});
    return () => c.abort();
  }, []);
  return hosted ? (
    <div
      role="note"
      className="border-b border-amber-300 bg-amber-50 px-5 py-3 text-xs text-amber-950"
    >
      Hosted API mode: admitted document text is sent to Groq after explicit
      consent. Direct identifier masking is limited, not complete anonymization.
      Optional source verification is disclosed separately. Documents are
      temporarily stored on this server until deletion or expiry; provider
      policies also apply.
    </div>
  ) : null;
}
