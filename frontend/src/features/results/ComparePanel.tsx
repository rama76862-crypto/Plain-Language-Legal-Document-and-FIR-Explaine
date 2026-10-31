import { useEffect, useRef, useState } from "react";
import { useSession } from "../../lib/session";
import {
  createDocument,
  getDocument,
  getExtraction,
  patchExtraction,
  deleteDocument,
  compareDocuments,
  ApiClientError,
} from "../../lib/api";
import type { Clause, DocumentCreateResponse, CompareResponse } from "../../lib/types";
import { GlassCard, Button } from "../../design/primitives";
import { useT } from "../../lib/i18n";

export function ComparePanel({
  onNavigateEvidence,
}: {
  onNavigateEvidence: (id: string) => void;
}) {
  const { t } = useT();
  const { documentId, sessionToken, revision, inputLanguage, documentType } =
    useSession();
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [reviewed, setReviewed] = useState(false);
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const second = useRef<DocumentCreateResponse | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    setFile(null);
    setConsent(false);
    setReviewed(false);
    setClauses([]);
    setBusy(false);
    setError("");
    setComparison(null);
    return () => {
      abort.current?.abort();
      const doc = second.current;
      second.current = null;
      if (doc)
        void deleteDocument(doc.document_id, doc.session_token).catch(() => {});
    };
  }, [documentId]);

  async function extract() {
    if (!file || !consent) return;
    setBusy(true);
    setError("");
    setComparison(null);
    setReviewed(false);
    const controller = new AbortController();
    abort.current = controller;
    try {
      if (second.current) {
        await deleteDocument(
          second.current.document_id,
          second.current.session_token,
        );
        second.current = null;
      }
      const uploaded = await createDocument(
        file,
        inputLanguage === "unknown" ? "auto" : inputLanguage,
        documentType,
        controller.signal,
        consent,
      );
      second.current = uploaded;
      const deadline = Date.now() + 120000;
      let ready = false;
      while (Date.now() < deadline) {
        const meta = await getDocument(
          uploaded.document_id,
          uploaded.session_token,
          controller.signal,
        );
        if (meta.extraction_ready) {
          ready = true;
          break;
        }
        if (meta.status === "failed")
          throw new Error(t("compare.extractionFailed"));
        await new Promise((resolve) => setTimeout(resolve, 700));
        if (controller.signal.aborted) return;
      }
      if (!ready) throw new Error(t("compare.extractionNotReady"));
      const extracted = await getExtraction(
        uploaded.document_id,
        uploaded.session_token,
        controller.signal,
      );
      if (!controller.signal.aborted) setClauses(extracted.clauses);
    } catch (e: unknown) {
      if (!controller.signal.aborted) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        const msg =
          e instanceof ApiClientError
            ? e.message
            : e instanceof Error
            ? e.message
            : t("compare.extractionUnavailable");
        setError(msg || t("compare.extractionUnavailable"));
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  async function compare() {
    const b = second.current;
    if (!b || !reviewed || !documentId || !sessionToken) return;
    setBusy(true);
    setError("");
    const controller = new AbortController();
    abort.current = controller;
    try {
      const corrected = await patchExtraction(
        b.document_id,
        b.session_token,
        {
          expected_revision: b.revision,
          corrections: clauses.map((c) => ({
            clause_id: c.clause_id,
            text: c.reviewed_text,
          })),
          input_language: inputLanguage,
          document_type: documentType,
        },
        controller.signal
      );
      b.revision = corrected.revision;

      const data = await compareDocuments(
        documentId,
        sessionToken,
        b.document_id,
        b.session_token,
        revision,
        corrected.revision,
        controller.signal
      );
      if (!controller.signal.aborted) setComparison(data);
    } catch (e: unknown) {
      if (!controller.signal.aborted) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        const msg =
          e instanceof ApiClientError
            ? e.message
            : e instanceof Error
            ? e.message
            : t("compare.comparisonFailed");
        setError(msg || t("compare.comparisonFailed"));
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const handleCopySummary = async () => {
    if (!comparison) return;
    const lines: string[] = [];
    lines.push(`# ${t("compare.title")}\n`);
    lines.push(
      t("compare.changesSummary", {
        changes: comparison.changes.length,
        unchanged: comparison.unchanged_passages,
      }) + "\n"
    );

    comparison.changes.forEach((c, idx) => {
      const changeTypeLabel =
        c.change_type === "modified"
          ? t("compare.modified")
          : c.change_type === "added"
          ? t("compare.added")
          : c.change_type === "removed"
          ? t("compare.removed")
          : c.change_type;
      lines.push(`### Change ${idx + 1}: ${changeTypeLabel}`);
      lines.push(
        `- **${t("compare.beforeA")}**: ${
          c.before
            ? `"${c.before.quote}" (${c.before.clause_id})`
            : t("compare.noMatchingPassage")
        }`
      );
      lines.push(
        `- **${t("compare.afterB")}**: ${
          c.after
            ? `"${c.after.quote}" (${c.after.clause_id})`
            : t("compare.noMatchingPassage")
        }`
      );
      if (c.why_review) {
        lines.push(`- **Review**: ${c.why_review}`);
      }
      lines.push("");
    });

    if (comparison.limitations.length > 0) {
      lines.push(`## Limitations\n`);
      comparison.limitations.forEach((text) => lines.push(`- ${text}`));
    }

    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    } catch {
      // clipboard fallback
    }
  };

  return (
    <div className="space-y-4">
      <GlassCard className="p-5 space-y-4">
        <h3 className="text-lg font-bold text-navy">{t("compare.title")}</h3>
        <p className="text-xs text-mute">{t("compare.sub")}</p>
        <input
          aria-label={t("compare.fileAriaLabel")}
          type="file"
          accept=".pdf,.docx"
          disabled={busy}
          className="text-xs text-navy file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue/10 file:text-blue hover:file:bg-blue/20 cursor-pointer"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setComparison(null);
            setClauses([]);
            setReviewed(false);
          }}
        />
        <label className="flex items-start gap-2 text-sm text-navy cursor-pointer">
          <input
            type="checkbox"
            className="mt-1 rounded border-line"
            checked={consent}
            disabled={busy}
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span>{t("compare.consent")}</span>
        </label>
        <div>
          <Button disabled={busy || !file || !consent} onClick={extract}>
            {t("compare.extractButton")}
          </Button>
        </div>
        {error && (
          <p role="alert" className="text-xs text-concern font-medium">
            {error}
          </p>
        )}
        {busy && <p role="status" className="text-xs text-mute font-mono">{t("compare.busy")}</p>}
        {clauses.length > 0 && (
          <>
            <div className="max-h-96 overflow-auto space-y-3">
              {clauses.map((c, i) => (
                <label key={c.clause_id} className="block text-xs text-mute">
                  {t("compare.clauseLabel", { index: i + 1 })}
                  <textarea
                    className="block w-full p-3 rounded border border-line bg-paper text-navy mt-1 focus:ring-1 focus:ring-blue focus:outline-none"
                    rows={4}
                    maxLength={10000}
                    disabled={busy}
                    value={c.reviewed_text}
                    onChange={(e) => {
                      setReviewed(false);
                      setComparison(null);
                      setClauses((all) =>
                        all.map((x) =>
                          x.clause_id === c.clause_id
                            ? { ...x, reviewed_text: e.target.value }
                            : x,
                        ),
                      );
                    }}
                  />
                </label>
              ))}
            </div>
            <label className="flex items-center gap-2 text-sm text-navy cursor-pointer">
              <input
                type="checkbox"
                className="rounded border-line"
                checked={reviewed}
                disabled={busy}
                onChange={(e) => setReviewed(e.target.checked)}
              />
              <span>{t("compare.reviewConfirm")}</span>
            </label>
            <div>
              <Button disabled={busy || !reviewed} onClick={compare}>
                {t("compare.compareButton")}
              </Button>
            </div>
          </>
        )}
      </GlassCard>
      {comparison && (
        <GlassCard className="p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-line pb-3">
            <h3 className="font-bold text-navy">
              {t("compare.changesSummary", {
                changes: comparison.changes.length,
                unchanged: comparison.unchanged_passages,
              })}
            </h3>
            <Button size="sm" variant="secondary" onClick={handleCopySummary}>
              {copied ? t("compare.copiedToast") : t("compare.copySummary")}
            </Button>
          </div>
          {comparison.changes.map((change) => {
            const changeTypeLabel =
              change.change_type === "modified"
                ? t("compare.modified")
                : change.change_type === "added"
                ? t("compare.added")
                : change.change_type === "removed"
                ? t("compare.removed")
                : change.change_type;

            return (
              <div
                key={change.change_id}
                className="p-4 border border-line rounded-lg space-y-3 bg-paper/50"
              >
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-blue/10 text-blue">
                    {changeTypeLabel}
                  </span>
                </div>
                <div className="grid md:grid-cols-2 gap-3">
                  {(["before", "after"] as const).map((side) => (
                    <div
                      key={side}
                      className={`p-3 rounded border transition-colors ${
                        side === "before"
                          ? "bg-concern-bg/35 border-concern/25"
                          : "bg-ok-bg/35 border-ok/25"
                      }`}
                    >
                      <strong className={`text-xs font-semibold flex items-center gap-1.5 ${side === "before" ? "text-concern-ink" : "text-ok-ink"}`}>
                        <span className={`w-2 h-2 rounded-full ${side === "before" ? "bg-concern" : "bg-ok"}`} />
                        {side === "before" ? t("compare.beforeA") : t("compare.afterB")}
                      </strong>
                      <blockquote className="text-xs text-navy/90 whitespace-pre-wrap mt-2 font-serif italic border-l-2 border-line/60 pl-2">
                        {change[side]?.quote ?? t("compare.noMatchingPassage")}
                      </blockquote>
                      {change[side] && (
                        <p className="text-[11px] font-mono text-mute mt-2">
                          {change[side]!.clause_id} ·{" "}
                          {change[side]!.source_ref.page_number
                            ? t("compare.pageLabel", { page: change[side]!.source_ref.page_number })
                            : t("compare.paraLabel", { para: change[side]!.source_ref.paragraph_index ?? 1 })}
                        </p>
                      )}
                      {side === "before" && change.before && (
                        <div className="mt-2">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() =>
                              onNavigateEvidence(change.before!.clause_id)
                            }
                          >
                            {t("compare.openSourceA")}
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                {change.why_review && (
                  <p className="text-xs text-mute">{change.why_review}</p>
                )}
              </div>
            );
          })}
          {comparison.limitations.map((text) => (
            <p key={text} className="text-xs text-mute">
              {text}
            </p>
          ))}
        </GlassCard>
      )}
    </div>
  );
}
export default ComparePanel;
