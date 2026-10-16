import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import ts from 'typescript';
import * as progress from '../src/lib/product-progress.ts';

async function client() {
  const source = await readFile(new URL('../src/lib/api-core.ts', import.meta.url), 'utf8');
  const progressUrl = new URL('../src/lib/product-progress.ts', import.meta.url).href;
  const js = ts.transpileModule(source.replace(/import .*config.*;/, 'const API_URL = "/api";')
    .replace('"@/lib/product-progress"', JSON.stringify(progressUrl)), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 },
  }).outputText;
  const clientModule = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}#${Math.random()}`);
  return { ...clientModule, api: clientModule.createApi({ header: async () => ({}) }) };
}

for (const status of [404, 503]) {
  test(`API error ${status} preserves status and readable message`, async t => {
    const previous = globalThis.fetch;
    t.after(() => { globalThis.fetch = previous; });
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Source unavailable' }), { status });
    const { api, ApiError } = await client();
    await assert.rejects(api.getBrand('example'), error =>
      error instanceof ApiError && error.status === status && error.message === 'Source unavailable');
  });
}

test('authentication failure remains distinguishable from a missing resource', async t => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 });
  const { api, ApiError, UnauthorizedError } = await client();
  await assert.rejects(api.getCurrentUser(), error =>
    error instanceof UnauthorizedError && error instanceof ApiError && error.status === 401);
});

test('provider failures and raw server bodies do not leak implementation details', async t => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  for (const body of [JSON.stringify({ detail: 'sonnet CLI failed: subscription unavailable' }), '<html>Traceback: secret diagnostic</html>']) {
    globalThis.fetch = async () => new Response(body, { status: 503 });
    const { api } = await client();
    await assert.rejects(api.getBrand('example'), error => {
      assert.doesNotMatch(error.message, /sonnet|CLI|Traceback|diagnostic|html/);
      assert.match(error.message, /retry|try again/);
      return true;
    });
  }
  assert.equal(progress.problemText('Insufficient credits. Add credits to continue.'), 'Insufficient credits. Add credits to continue.');
});

test('a failed response is not reused as an empty successful answer', async t => {
  const previous = globalThis.fetch;
  t.after(() => { globalThis.fetch = previous; });
  let calls = 0;
  globalThis.fetch = async () => ++calls === 1
    ? new Response(JSON.stringify({ detail: 'Temporary outage' }), { status: 503 })
    : new Response(JSON.stringify({ name: 'Recovered brand' }), { status: 200 });
  const { api } = await client();
  await assert.rejects(api.getBrand('example'));
  assert.equal((await api.getBrand('example')).name, 'Recovered brand');
  assert.equal(calls, 2);
});

test('an optional resource is empty only when the server actually returns 404', async () => {
  const { ApiError, nullIfMissing } = await client();
  assert.equal(nullIfMissing(new ApiError('Not compiled', 404)), null);
  for (const error of [new ApiError('Database unavailable', 503), new TypeError('Network failure')]) {
    assert.throws(() => nullIfMissing(error), actual => actual === error);
  }
});
