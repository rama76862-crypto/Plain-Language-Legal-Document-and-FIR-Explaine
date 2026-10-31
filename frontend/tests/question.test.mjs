import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import React from 'react';
import { act, create } from 'react-test-renderer';
import { createServer } from 'vite';

let server, QuestionPanel, ResultProvider, SessionProvider, useSession, I18nProvider;
const json = (value, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } });
const answer = { answer: 'The monthly fee is INR 1500.', evidence: [], reference_ids: [], review_status: 'needs_review', limitations: [] };
const text = node => typeof node === 'string' ? node : (node.children || []).map(text).join('');
before(async () => {
  server = await createServer({ configFile: false, server: { middlewareMode: true, hmr: false, ws: false },
    optimizeDeps: { noDiscovery: true, include: [] }, appType: 'custom' });
  ({ QuestionPanel } = await server.ssrLoadModule('/src/features/results/QuestionPanel.tsx'));
  ({ ResultProvider } = await server.ssrLoadModule('/src/features/results/ResultContext.tsx'));
  ({ SessionProvider, useSession } = await server.ssrLoadModule('/src/lib/session.tsx'));
  ({ I18nProvider } = await server.ssrLoadModule('/src/lib/i18n.tsx'));
});
after(async () => server?.close());

async function harness(t, handleQuestion) {
  let session, renderer;
  globalThis.window = new EventTarget();
  t.after(() => { act(() => renderer?.unmount()); delete globalThis.window; });
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    if (String(url).endsWith('/questions')) return handleQuestion(JSON.parse(init.body), init.signal);
    if (init.method === 'POST') return json({ analysis_id: 'a1', status: 'queued', document_revision: 1 });
    if (String(url).endsWith('/analyses/a1')) return json({ status: 'needs_review',
      progress: { completed_clauses: 1, total_clauses: 1 }, result: { analysis_id: 'a1', output_language: 'en', references: [] } });
    return json({ expires_at: new Date(Date.now() + 1800000).toISOString() });
  });
  function Capture() { session = useSession(); return null; }
  await act(async () => {
    renderer = create(React.createElement(I18nProvider, null,
      React.createElement(SessionProvider, null,
        React.createElement(Capture),
        React.createElement(ResultProvider, { documentId: 'doc', sessionToken: 'test-token', revision: 1, initialOutputLanguage: 'en' },
          React.createElement(QuestionPanel, { onNavigateEvidence: () => {} })))));
  });
  await act(async () => session.startSession({ documentId: 'doc', sessionToken: 'test-token', revision: 1,
    filename: 'synthetic.docx', inputLanguage: 'en', outputLanguage: 'en', documentType: 'agreement' }));
  return {
    renderer,
    async send(question) {
      act(() => renderer.root.findByType('textarea').props.onChange({ target: { value: question } }));
      await act(async () => renderer.root.findByType('form').props.onSubmit({ preventDefault() {} }));
    },
    button(label) { return renderer.root.findAllByType('button').find(node => text(node) === label); },
  };
}

test('Ask shows the real model error and retries the same question ID', async (t) => {
  const requests = [];
  const ui = await harness(t, payload => {
    requests.push(payload);
    return requests.length === 1
      ? json({ error: { code: 'MODEL_UNAVAILABLE', message: 'The local model is unavailable.', retryable: true } }, 503)
      : json(answer);
  });
  await ui.send('What is the monthly fee?');
  assert.ok(text(ui.renderer.root).includes('The local model is unavailable.'));
  assert.ok(!text(ui.renderer.root).includes('Could not connect to the local NyayaSarathi API server.'));
  await act(async () => ui.button('Retry Analysis').props.onClick());
  assert.equal(requests.length, 2);
  assert.equal(requests[0].client_request_id, requests[1].client_request_id);
  assert.ok(text(ui.renderer.root).includes(answer.answer));
});

test('Ask displays a context-limit explanation without offering an identical retry', async (t) => {
  const ui = await harness(t, () => json({ error: { code: 'MODEL_CONTEXT_LIMIT',
    message: 'Ask a shorter question about one clause.', retryable: false } }, 422));
  await ui.send('What is the monthly fee?');
  assert.ok(text(ui.renderer.root).includes('Ask a shorter question about one clause.'));
  assert.equal(ui.button('Retry Analysis'), undefined);
});

test('a cancelled response cannot clear loading or add history for a newer question', async (t) => {
  const pending = [];
  const ui = await harness(t, () => new Promise(resolve => pending.push(resolve)));
  await ui.send('What is the monthly fee?');
  act(() => ui.button('Cancel').props.onClick());
  await ui.send('When is the monthly fee due?');
  await act(async () => pending[0](json(answer)));
  assert.equal(ui.renderer.root.findByType('textarea').props.disabled, true);
  assert.ok(!text(ui.renderer.root).includes(answer.answer));
  await act(async () => pending[1](json(answer)));
  assert.equal(ui.renderer.root.findByType('textarea').props.disabled, false);
  assert.ok(text(ui.renderer.root).includes('History: 1/20'));
});
