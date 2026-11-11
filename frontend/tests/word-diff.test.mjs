import assert from 'node:assert/strict';
import { test } from 'node:test';
import { diffStats, diffWords } from '../src/lib/word-diff.ts';

const join = (parts, kinds) => parts.filter(p => kinds.includes(p.kind)).map(p => p.text).join('');

test('reconstructs both versions exactly from the parts', () => {
  const before = 'Hi there,\n\nThis email is far too long and it rambles.\n\n- Ana';
  const after = 'Hi there,\n\nThis email is short.\n\n- Ana';
  const parts = diffWords(before, after);
  assert.equal(join(parts, ['same', 'removed']), before);
  assert.equal(join(parts, ['same', 'added']), after);
});

test('merges a changed phrase into one highlight', () => {
  const parts = diffWords('one two three four', 'one five six four');
  assert.deepEqual(parts.map(p => p.kind), ['same', 'removed', 'added', 'same']);
  assert.deepEqual(diffStats(parts), { added: 2, removed: 2 });
});

test('identical text has nothing added or removed', () => {
  const parts = diffWords('Same words here.', 'Same words here.');
  assert.deepEqual(diffStats(parts), { added: 0, removed: 0 });
});

test('a very long input degrades to lines instead of freezing', () => {
  const before = Array.from({ length: 900 }, (_, i) => `word${i}`).join(' ');
  const after = `${before}\nnew line`;
  const parts = diffWords(before, after);
  assert.equal(join(parts, ['same', 'added']), after);
});
