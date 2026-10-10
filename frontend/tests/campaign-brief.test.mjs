import assert from 'node:assert/strict';
import { test } from 'node:test';
import { customEmailRequest } from '../src/lib/campaign-brief.ts';

test('keeps the selected count ahead of freeform instructions and preserves the brief', () => {
  assert.equal(customEmailRequest(3, '  Explain the kit.\nThen answer a concern.  '),
    'Write exactly 3 emails.\n\nExplain the kit.\nThen answer a concern.');
});

test('refuses empty instructions and counts outside the supported contract', () => {
  for (const count of [0, 13, 1.5, NaN]) assert.throws(() => customEmailRequest(count, 'A complete brief.'), /between 1 and 12/);
  assert.throws(() => customEmailRequest(1, '          '), /at least 10/);
});
