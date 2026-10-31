import { useRef, useState } from "react";
import { useSession } from "../../lib/session";
import { useResult } from "./ResultContext";
import { verifySource, ApiClientError } from "../../lib/api";
import { Button, GlassCard } from "../../design/primitives";
import { useT } from "../../lib/i18n";
import { CheckCircle, AlertTriangle, Info } from "lucide-react";

export function SourceVerificationPanel({
  onNavigateEvidence,
}: {
  onNavigateEvidence: (id: string) => void;
}) {
  const { t } = useT();
  const { documentId, sessionToken } = useSession();
  const { result, verificationResult, setVerificationResult } = useResult();
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const abort = useRef<AbortController | null>(null);

  const check = verificationResult;

  async function verify() {
    if (!consent || !documentId || !sessionToken || !result?.analysis_id) return;
    setBusy(true);
    setError("");
    const c = new AbortController();
    abort.current = c;
    try {
      const data = await verifySource(
        documentId,
        sessionToken,
        result.analysis_id,
        true,
        c.signal
      );
      if (!c.signal.aborted) {
        setVerificationResult(data);
      }
    } catch (e: unknown) {
      if (!c.signal.aborted) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        const msg =
          e instanceof ApiClientError
            ? e.message
            : e instanceof Error
            ? e.message
            : t("verify.unavailable");
        setError(msg || t("verify.unavailable"));
      }
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }

  return (
    <GlassCard className="p-5 space-y-4">
      <div>
        <h3 className="font-bold text-navy text-lg">{t("verify.title")}</h3>
        <p className="text-xs text-mute mt-1">{t("verify.sub")}</p>
      </div>

      <label className="flex items-start gap-3 text-sm text-navy cursor-pointer">
        <input
          type="checkbox"
          className="mt-1 rounded border-line"
          checked={consent}
          disabled={busy}
          onChange={(e) => setConsent(e.target.checked)}
        />
        <span>{t("verify.consent")}</span>
      </label>

      <div>
        <Button disabled={!consent || busy} onClick={verify}>
          {busy ? t("verify.checkingButton") : t("verify.checkButton")}
        </Button>
      </div>

      {error && (
        <p role="alert" className="text-xs text-error font-medium">
          {error}
        </p>
      )}

      {check && (
        <div className="space-y-4 pt-2 border-t border-line">
          {/* Status Badge */}
          {check.status === "cross_checked" && (
            <div className="flex items-center gap-3 p-3.5 rounded-lg bg-ok/10 border border-ok/20 text-ok">
              <CheckCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="text-xs font-bold">{t("verify.badgeCrossChecked")}</p>
                <p className="text-[11px] text-ok/80 font-medium">
                  {t("verify.statusCrossChecked")}
                </p>
              </div>
            </div>
          )}

          {check.status === "needs_review" && (
            <div className="flex items-center gap-3 p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-900">
              <AlertTriangle className="w-5 h-5 shrink-0 text-amber-600" />
              <div>
                <p className="text-xs font-bold">{t("verify.badgeNeedsReview")}</p>
                <p className="text-[11px] text-amber-800 font-medium">
                  {t("verify.statusNeedsReview")}
                </p>
              </div>
            </div>
          )}

          {check.status === "unavailable" && (
            <div className="flex items-center gap-3 p-3.5 rounded-lg bg-bg2/60 border border-line text-mute">
              <Info className="w-5 h-5 shrink-0 text-blue" />
              <div>
                <p className="text-xs font-bold text-navy">
                  {t("verify.badgeUnavailable")}
                </p>
                <p className="text-[11px]">
                  {check.reason || t("verify.statusUnavailable")}
                </p>
              </div>
            </div>
          )}

          <p className="text-xs text-mute font-mono">
            {t("verify.claimsCheckedSummary", {
              checked: check.checked_claims,
              selected: check.selected_claims,
              reason: check.reason ? `(${check.reason})` : "",
            })}
          </p>

          {check.issues && check.issues.length > 0 && (
            <div className="space-y-3">
              {check.issues.map((issue, i) => (
                <div
                  key={i}
                  className="p-3.5 border border-line rounded-lg space-y-2.5 bg-paper/50"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                        issue.verdict === "contradicts"
                          ? "bg-red-500/10 text-red-700 border border-red-500/20"
                          : issue.verdict === "unclear"
                          ? "bg-amber-500/10 text-amber-800 border border-amber-500/20"
                          : "bg-ok/10 text-ok border border-ok/20"
                      }`}
                    >
                      {issue.verdict === "contradicts"
                        ? t("verify.verdictContradicts")
                        : issue.verdict === "unclear"
                        ? t("verify.verdictUnclear")
                        : t("verify.verdictSupported")}
                    </span>
                    <span className="text-[11px] font-mono text-mute">
                      {issue.clause_id}
                    </span>
                  </div>
                  <p className="text-xs text-navy leading-relaxed">
                    {issue.message}
                  </p>
                  <div>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => onNavigateEvidence(issue.clause_id)}
                    >
                      {t("verify.openClause", { id: issue.clause_id })}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {check.limitation && (
            <p className="text-xs text-mute leading-relaxed">{check.limitation}</p>
          )}
        </div>
      )}
    </GlassCard>
  );
}
export default SourceVerificationPanel;
