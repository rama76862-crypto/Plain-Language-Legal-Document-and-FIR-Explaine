import { useEffect, useRef, useState } from "react";
import { useSession } from "../../lib/session";
import { useResult } from "./ResultContext";
import { config } from "../../lib/config";
import { Button, GlassCard } from "../../design/primitives";
type Check = {
  status: "cross_checked" | "needs_review" | "unavailable";
  checked_claims: number;
  selected_claims: number;
  reason?: string;
  limitation: string;
  issues: Array<{ clause_id: string; verdict: string; message: string }>;
};
export function SourceVerificationPanel({
  onNavigateEvidence,
}: {
  onNavigateEvidence: (id: string) => void;
}) {
  const { documentId, sessionToken } = useSession();
  const { result } = useResult();
  const [consent, setConsent] = useState(false);
  const [check, setCheck] = useState<Check | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const abort = useRef<AbortController | null>(null);
  useEffect(() => {
    setCheck(null);
    setConsent(false);
    setError("");
    setBusy(false);
    return () => abort.current?.abort();
  }, [documentId, result?.analysis_id]);
  async function verify() {
    if (!consent || !documentId || !sessionToken || !result) return;
    setBusy(true);
    setError("");
    const c = new AbortController();
    abort.current = c;
    try {
      const response = await fetch(
        `${config.apiBaseUrl}/documents/${encodeURIComponent(documentId)}/analyses/${encodeURIComponent(result.analysis_id)}/verify-source`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Session-Token": sessionToken,
          },
          body: JSON.stringify({ external_ai_consent: true }),
          signal: c.signal,
        },
      );
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.error?.message ?? "Source check unavailable.");
      if (!c.signal.aborted) setCheck(data);
    } catch (e) {
      if (!c.signal.aborted)
        setError(e instanceof Error ? e.message : "Source check unavailable.");
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }
  return (
    <GlassCard className="p-5 space-y-4">
      <h3 className="font-bold">Optional second-model source check</h3>
      <p className="text-xs text-mute">
        Cloudflare can check up to six selected explanations against their cited
        excerpts. This is a limited source comparison, not independent legal or
        fluent-language review.
      </p>
      <label className="flex gap-3 text-sm">
        <input
          type="checkbox"
          checked={consent}
          disabled={busy}
          onChange={(e) => setConsent(e.target.checked)}
        />
        I consent to these selected claims and excerpts being sent to Cloudflare
        Workers AI. Direct identifier masking is limited; provider policies
        apply.
      </label>
      <Button disabled={!consent || busy} onClick={verify}>
        {busy ? "Checking selected claims…" : "Check cited source claims"}
      </Button>
      {error && <p role="alert">{error}</p>}
      {check && (
        <div className="space-y-3">
          <p className="font-semibold">
            {check.status === "cross_checked"
              ? "Selected claims agreed with the cited source"
              : check.status === "needs_review"
                ? "Source disagreements need review"
                : "Verifier unavailable"}
          </p>
          <p className="text-xs">
            {check.checked_claims} of {check.selected_claims} selected claims
            checked. {check.reason}
          </p>
          {check.issues.map((issue, i) => (
            <div key={i} className="p-3 border border-line rounded">
              <p className="text-sm">
                {issue.verdict}: {issue.message}
              </p>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onNavigateEvidence(issue.clause_id)}
              >
                Open {issue.clause_id}
              </Button>
            </div>
          ))}
          <p className="text-xs text-mute">{check.limitation}</p>
        </div>
      )}
    </GlassCard>
  );
}
