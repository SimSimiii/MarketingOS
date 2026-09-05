import assert from 'node:assert/strict';
import { test } from 'node:test';
import { startVisiblePolling } from '../src/lib/visible-polling.ts';

class Visibility extends EventTarget {
  hidden = false;
  change(hidden) {
    this.hidden = hidden;
    this.dispatchEvent(new Event('visibilitychange'));
  }
}

const flush = async () => { await Promise.resolve(); await Promise.resolve(); };

test('slow requests never overlap and the next delay starts after completion', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const visibility = new Visibility();
  let calls = 0;
  let finish;
  const stop = startVisiblePolling(() => {
    calls++;
    return new Promise(resolve => { finish = resolve; });
  }, 4000, visibility);
  t.after(stop);
  t.mock.timers.tick(4000);
  assert.equal(calls, 1);
  t.mock.timers.tick(20000);
  visibility.change(true);
  visibility.change(false);
  assert.equal(calls, 1);
  finish();
  await flush();
  t.mock.timers.tick(3999);
  assert.equal(calls, 1);
  t.mock.timers.tick(1);
  assert.equal(calls, 2);
  stop();
  finish();
  await flush();
  t.mock.timers.tick(20000);
  assert.equal(calls, 2);
});

test('hidden tabs pause and resume once immediately; disposal removes the listener', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const visibility = new Visibility();
  visibility.hidden = true;
  let calls = 0;
  const stop = startVisiblePolling(async () => { calls++; }, 4000, visibility);
  t.after(stop);
  t.mock.timers.tick(20000);
  assert.equal(calls, 0);
  visibility.change(false);
  assert.equal(calls, 1);
  await flush();
  visibility.change(true);
  t.mock.timers.tick(20000);
  assert.equal(calls, 1);
  visibility.change(false);
  await flush();
  assert.equal(calls, 2);
  stop();
  visibility.change(true);
  visibility.change(false);
  t.mock.timers.tick(20000);
  assert.equal(calls, 2);
});

test('completion while hidden does not restart polling', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] });
  const visibility = new Visibility();
  let calls = 0;
  let finish;
  const stop = startVisiblePolling(() => {
    calls++;
    return new Promise(resolve => { finish = resolve; });
  }, 4000, visibility);
  t.after(stop);
  t.mock.timers.tick(4000);
  visibility.change(true);
  finish();
  await flush();
  t.mock.timers.tick(20000);
  assert.equal(calls, 1);
});
