import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';

async function loadRefresh() {
  const source = await readFile(new URL('../src/lib/renew-session.ts', import.meta.url), 'utf8');
  const js = ts.transpileModule(source.replace(/import .*auth-cookies.*;/,
    'const ACCESS_TOKEN_COOKIE = "mos_access_token";'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
  }).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}#${Math.random()}`);
}

function browser(t, fetcher) {
  const previous = ['document', 'navigator', 'fetch'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]);
  let queued = Promise.resolve();
  Object.defineProperty(globalThis, 'document', { configurable: true, value: { cookie: '' } });
  Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { locks: {
    request(_name, action) {
      const result = queued.then(action);
      queued = result.catch(() => {});
      return result;
    },
  } } });
  globalThis.fetch = fetcher;
  t.after(() => previous.forEach(([key, descriptor]) => {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else delete globalThis[key];
  }));
}

test('expired access cookie: concurrent requests and tabs rotate the refresh token once', async t => {
  let calls = 0;
  browser(t, async (_url, init) => {
    calls++;
    assert.equal(init.credentials, 'same-origin');
    document.cookie = 'mos_access_token=renewed';
    return new Response(null, { status: 200 });
  });
  const first = await loadRefresh();
  const second = await loadRefresh();
  assert.deepEqual(await Promise.all([first.renewSession(), first.renewSession(), second.renewSession()]), [true, true, true]);
  assert.equal(calls, 1);
});

test('temporary refresh outage permits a later retry', async t => {
  let calls = 0;
  browser(t, async () => new Response(null, { status: ++calls === 1 ? 503 : 200 }));
  const { renewSession } = await loadRefresh();
  await assert.rejects(renewSession(), /unavailable/);
  assert.equal(await renewSession(), true);
});

test('revoked refresh token returns signed-out without retrying forever', async t => {
  let calls = 0;
  browser(t, async () => { calls++; return new Response(null, { status: 401 }); });
  const { renewSession } = await loadRefresh();
  assert.equal(await renewSession(), false);
  assert.equal(calls, 1);
});
