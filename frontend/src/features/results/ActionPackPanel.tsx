import { useEffect, useState } from "react";
import { useSession } from "../../lib/session";
import { useResult } from "./ResultContext";
import { getActionPack, ApiClientError } from "../../lib/api";
import { GlassCard, Button } from "../../design/primitives";
import { useT } from "../../lib/i18n";
import type { ActionPackResponse } from "../../lib/types";

export function ActionPackPanel({
  onNavigateEvidence,
}: {
  onNavigateEvidence: (id: string) => void;
}) {
  const { t } = useT();
  const { documentId, sessionToken } = useSession();
  const {
    result,
    checkedObligations,
    toggleObligation,
    setPrefilledQuestion,
    setActiveTab,
    actionPack,
    setActionPack,
  } = useResult();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!documentId || !sessionToken || !result?.analysis_id) return;

    // If context already holds the action pack for this analysis, no need to refetch
    if (actionPack && actionPack.analysis_id === result.analysis_id) {
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError("");

    getActionPack(documentId, sessionToken, result.analysis_id, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setActionPack(data);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (!controller.signal.aborted) {
          if (e instanceof DOMException && e.name === "AbortError") return;
          const msg = e instanceof ApiClientError ? e.message : e instanceof Error ? e.message : t("actionPack.unavailable");
          setError(msg || t("actionPack.unavailable"));
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [documentId, sessionToken, result?.analysis_id, actionPack, setActionPack, t]);

  const pack: ActionPackResponse | null = actionPack;

  const handleCopy = async () => {
    if (!pack) return;
    const lines: string[] = [];
    lines.push(`# ${t("actionPack.title")}\n`);
    lines.push(`## ${t("tabs.actionPack")}\n`);
    pack.checklist.forEach((item) => {
      const isChecked = checkedObligations.has(item.id);
      const mark = isChecked ? "[x]" : "[ ]";
      const party =
        item.party === "not_detected"
          ? t("actionPack.noRole")
          : t("actionPack.roleWords", { party: item.party });
      lines.push(`- ${mark} **${item.statement}**`);
      lines.push(`  - ${party}`);
      if (item.due_or_trigger.length > 0) {
        lines.push(
          `  - ${item.due_or_trigger.map((text) => t("actionPack.periodTrigger", { text })).join("; ")}`
        );
      }
      lines.push(`  - Clause ID: ${item.clause_id}`);
    });

    if (pack.lawyer_questions.length > 0) {
      lines.push(`\n## ${t("actionPack.questionsTitle")}\n`);
      pack.lawyer_questions.forEach((q, idx) => {
        lines.push(`${idx + 1}. **${q.question}**`);
        if (q.clause_ids.length > 0) {
          lines.push(`   - Clauses: ${q.clause_ids.join(", ")}`);
        }
      });
    }

    if (pack.limitations.length > 0) {
      lines.push(`\n## Limitations\n`);
      pack.limitations.forEach((text) => lines.push(`- ${text}`));
    }

    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      // Fallback if clipboard API is blocked
    }
  };

  return (
    <div className="space-y-4">
      <GlassCard className="p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold text-navy">{t("actionPack.title")}</h3>
            <p className="text-xs text-mute">{t("actionPack.sub")}</p>
          </div>
          {pack && (
            <Button size="sm" variant="secondary" onClick={handleCopy}>
              {copied ? t("actionPack.copiedToast") : t("actionPack.copyButton")}
            </Button>
          )}
        </div>

        {error && (
          <p role="alert" className="text-xs text-error font-medium">
            {error}
          </p>
        )}

        {loading && !pack && !error && (
          <p role="status" className="text-xs text-mute font-mono">
            {t("actionPack.loading")}
          </p>
        )}

        {pack?.checklist.length === 0 && (
          <p className="text-xs text-mute">{t("actionPack.empty")}</p>
        )}

        {pack?.checklist.map((item) => (
          <div
            key={item.id}
            className="p-4 border border-line rounded-lg space-y-2 bg-paper/50"
          >
            <label className="flex items-start gap-3 text-sm cursor-pointer">
              <input
                type="checkbox"
                className="mt-1 rounded border-line"
                checked={checkedObligations.has(item.id)}
                onChange={() => toggleObligation(item.id)}
              />
              <span className={checkedObligations.has(item.id) ? "line-through text-mute" : "text-navy font-medium"}>
                {item.statement}
              </span>
            </label>
            <p className="text-xs text-mute">
              {item.party === "not_detected"
                ? t("actionPack.noRole")
                : t("actionPack.roleWords", { party: item.party })}
            </p>
            {item.due_or_trigger.map((text) => (
              <p key={text} className="text-xs text-navy/80">
                {t("actionPack.periodTrigger", { text })}
              </p>
            ))}
            <div className="pt-1">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => onNavigateEvidence(item.clause_id)}
              >
                {t("actionPack.viewEvidence")}
              </Button>
            </div>
          </div>
        ))}
      </GlassCard>

      <GlassCard className="p-5 space-y-3">
        <h3 className="font-bold text-navy">{t("actionPack.questionsTitle")}</h3>
        {pack?.lawyer_questions.map((item, i) => (
          <div key={i} className="space-y-2 border-b border-line pb-3 last:border-b-0">
            <p className="text-sm font-medium text-navy">{item.question}</p>
            <div className="flex flex-wrap items-center gap-2">
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  setPrefilledQuestion(item.question);
                  setActiveTab("ask");
                }}
              >
                {t("actionPack.askInQa")}
              </Button>
              {item.clause_ids.map((id) => (
                <Button
                  key={id}
                  size="sm"
                  variant="secondary"
                  onClick={() => onNavigateEvidence(id)}
                >
                  {t("actionPack.showClause", { id })}
                </Button>
              ))}
            </div>
          </div>
        ))}
        {pack?.limitations.map((text) => (
          <p key={text} className="text-xs text-mute">
            {text}
          </p>
        ))}
      </GlassCard>
    </div>
  );
}
export default ActionPackPanel;
