import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { act, create } from 'react-test-renderer';
import { createServer } from 'vite';

let server, usePolling, ResultProvider, useResult, SessionProvider, useSession, api;
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const json = value => new Response(JSON.stringify(value), { headers: { 'Content-Type': 'application/json' } });
before(async () => {
  server = await createServer({ configFile: false, server: { middlewareMode: true, hmr: false, ws: false },
    optimizeDeps: { noDiscovery: true, include: [] }, appType: 'custom' });
  ({ usePolling } = await server.ssrLoadModule('/src/lib/usePolling.ts'));
  ({ ResultProvider, useResult } = await server.ssrLoadModule('/src/features/results/ResultContext.tsx'));
  ({ SessionProvider, useSession } = await server.ssrLoadModule('/src/lib/session.tsx'));
  api = await server.ssrLoadModule('/src/lib/api.ts');
});
after(async () => { await server?.close(); });

test('extraction polling survives screen renders and stops at the terminal response', async () => {
  let requests = 0, successes = 0, renderer;
  const poll = async () => ({ status: ++requests === 2 ? 'awaiting_review' : 'extracting' });
  function Screen() {
    usePolling(poll, {
      intervalMs: 80,
      shouldStop: doc => doc.status === 'awaiting_review',
      onSuccess: () => { successes++; },
    });
    return null;
  }
  try {
    await act(async () => { renderer = create(React.createElement(Screen)); });
    for (let i = 0; i < 5; i++) {
      await act(async () => { renderer.update(React.createElement(Screen)); });
    }
    assert.equal(requests, 1, 'rendering must not restart the request');
    await act(async () => { await sleep(100); });
    assert.equal(requests, 2);
    assert.equal(successes, 2);
    await act(async () => { renderer.update(React.createElement(Screen)); await sleep(100); });
    assert.equal(requests, 2, 'terminal extraction must stay stopped');
  } finally { act(() => renderer?.unmount()); }
});

test('late responses from a replaced document cannot complete the current extraction', async () => {
  let resolveOld, renderer;
  const received = [];
  const oldPoll = () => new Promise(resolve => { resolveOld = resolve; });
  const newPoll = async () => 'new';
  function Screen({ poll }) {
    usePolling(poll, { shouldStop: () => true, onSuccess: value => received.push(value) });
    return null;
  }
  try {
    await act(async () => { renderer = create(React.createElement(Screen, { poll: oldPoll })); });
    await act(async () => { renderer.update(React.createElement(Screen, { poll: newPoll })); });
    await act(async () => { resolveOld('old'); });
    assert.deepEqual(received, ['new']);
  } finally { act(() => renderer?.unmount()); }
});

test('polling backoff pauses after failures and manual retry starts one request', async () => {
  let renderer, controls, requests = 0;
  const poll = async () => { requests++; throw new Error('offline'); };
  function Screen() {
    controls = usePolling(poll, { backoff: [10, 10], shouldStop: () => false });
    return null;
  }
  try {
    await act(async () => { renderer = create(React.createElement(Screen)); });
    await act(async () => { await sleep(30); });
    assert.equal(requests, 2);
    assert.equal(controls.connectionLost, true);
    await act(async () => { renderer.update(React.createElement(Screen)); });
    assert.equal(requests, 2);
    await act(async () => { controls.retry(); });
    assert.equal(requests, 3);
  } finally { act(() => renderer?.unmount()); }
});

test('action pack, verification and checked obligations belong to the completed analysis', async (t) => {
  let current, renderer, count = 0;
  t.mock.method(globalThis, 'fetch', async (_url, init) => {
    if (init.method === 'POST') {
      const language = JSON.parse(init.body).output_language;
      return json({ analysis_id: `${language}-${++count}`, status: 'queued', document_revision: 1 });
    }
    const analysisId = String(_url).split('/').at(-1);
    return json({
      status: 'needs_review', progress: { completed_clauses: 1, total_clauses: 1 },
      result: { analysis_id: analysisId, output_language: analysisId.startsWith('hi') ? 'hi' : 'en', document_type: 'fir' },
    });
  });
  function Consumer() { current = useResult(); return null; }
  try {
    await act(async () => {
      renderer = create(React.createElement(ResultProvider, {
        documentId: 'doc', sessionToken: 'synthetic-token', revision: 1,
        initialOutputLanguage: 'en', documentType: 'fir',
      }, React.createElement(Consumer)));
    });
    assert.equal(current.status, 'needs_review');
    const oldVerificationSetter = current.setVerificationResult;
    const oldPackSetter = current.setActionPack;
    act(() => {
      current.setVerificationResult({ status: 'cross_checked', checked_claims: 1 });
      current.setActionPack({ analysis_id: current.analysisId, checklist: [] });
      current.toggleObligation('c1');
    });
    await act(async () => { await current.startAnalysis('hi'); });
    assert.equal(current.result.output_language, 'hi');
    assert.equal(current.verificationResult, null);
    assert.equal(current.actionPack, null);
    assert.equal(current.checkedObligations.size, 0);
    act(() => {
      oldVerificationSetter({ status: 'cross_checked' });
      oldPackSetter({ analysis_id: 'en-1' });
    });
    assert.equal(current.verificationResult, null, 'late verifier response must be discarded');
    assert.equal(current.actionPack, null, 'late action pack must be discarded');
  } finally { act(() => renderer?.unmount()); }
});

test('API client rejects HTML fallback while preserving structured errors and deletion', async (t) => {
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => new Response('<html>SPA fallback</html>', {
    headers: { 'Content-Type': 'text/html' },
  }));
  await assert.rejects(api.getCapabilities(), error => error.code === 'INVALID_RESPONSE');
  fetchMock.mock.mockImplementation(async () => json({ mode: 'fixture' }));
  await assert.rejects(api.getCapabilities(), error => error.code === 'SIMULATED_RESPONSE_REJECTED');
  fetchMock.mock.mockImplementation(async () => new Response(JSON.stringify({
    error: { code: 'REVISION_CONFLICT', message: 'Review changed.', retryable: false }, request_id: 'req_test',
  }), { status: 409, headers: { 'Content-Type': 'application/json' } }));
  await assert.rejects(api.getCapabilities(), error => error.code === 'REVISION_CONFLICT' && error.requestId === 'req_test');
  fetchMock.mock.mockImplementation(async () => new Response(null, { status: 204 }));
  await api.deleteDocument('doc', 'synthetic-token');
});

test('a server retention extension prevents an early local session wipe', async (t) => {
  let current, renderer;
  const now = Date.now();
  let expiry = new Date(now + 5000).toISOString();
  const requests = [];
  globalThis.window = new EventTarget();
  t.mock.timers.enable({ apis: ['Date', 'setInterval'], now });
  t.mock.method(globalThis, 'fetch', async (url, init) => {
    requests.push(init.method);
    assert.ok(String(url).endsWith('/documents/doc'));
    return json({ expires_at: expiry });
  });
  function Consumer() { current = useSession(); return null; }
  try {
    await act(async () => { renderer = create(React.createElement(SessionProvider, null, React.createElement(Consumer))); });
    await act(async () => { current.startSession({
      documentId: 'doc', sessionToken: 'synthetic-token', revision: 1,
      filename: 'synthetic.docx', inputLanguage: 'en', outputLanguage: 'en', documentType: 'agreement',
    }); });
    assert.equal(current.inactivityRemainingSeconds, 5);
    expiry = new Date(now + 1800000).toISOString();
    await act(async () => { t.mock.timers.tick(6000); });
    assert.equal(current.documentId, 'doc');
    assert.ok(current.inactivityRemainingSeconds > 1700);
    assert.ok(requests.length >= 2, 'expiry must be rechecked before deletion');
    assert.ok(requests.every(method => method === 'GET'), 'background sync must not extend retention or delete an active session');
  } finally {
    act(() => renderer?.unmount());
    delete globalThis.window;
  }
});

test('deletion animation tolerates a frame timestamp earlier than effect initialization', async (t) => {
  const { ShredDissolve } = await server.ssrLoadModule('/src/design/scenes/ShredDissolve.tsx');
  let renderer, frame, finished = 0;
  const radii = [];
  globalThis.window = { innerWidth: 800, innerHeight: 600 };
  globalThis.requestAnimationFrame = callback => { frame = callback; return 1; };
  globalThis.cancelAnimationFrame = () => {};
  t.mock.method(performance, 'now', () => 100);
  const ctx = new Proxy({}, { get: (_target, property) => property === 'arc'
    ? (_x, _y, radius) => { assert.ok(radius >= 0); radii.push(radius); }
    : () => {}, set: () => true });
  try {
    act(() => { renderer = create(React.createElement(ShredDissolve, { onDone: () => finished++ }), {
      createNodeMock: element => element.type === 'canvas' ? { getContext: () => ctx } : null,
    }); });
    act(() => frame(99));
    assert.equal(radii[0], 0);
    act(() => frame(1300));
    assert.equal(finished, 1);
  } finally {
    act(() => renderer?.unmount());
    delete globalThis.window;
    delete globalThis.requestAnimationFrame;
    delete globalThis.cancelAnimationFrame;
  }
});
