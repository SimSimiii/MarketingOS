import assert from 'node:assert/strict';
import { test } from 'node:test';
import { splitEmail } from '../src/lib/email-parts.ts';

test('splits the labelled subject and preview from the body', () => {
  const parts = splitEmail(
    'Subject: A delivered test is only one path\nPreview text: Compare it first.\n\nHi there,\n\nBody line.\n\n- the team',
  );
  assert.deepEqual(parts, {
    subject: 'A delivered test is only one path',
    preview: 'Compare it first.',
    body: 'Hi there,\n\nBody line.\n\n- the team',
  });
});

test('keeps an empty preview line rather than refusing the email', () => {
  const parts = splitEmail('Subject: Hello\nPreview text: \n\nBody');
  assert.equal(parts?.preview, '');
  assert.equal(parts?.body, 'Body');
});

test('tolerates CRLF line endings', () => {
  assert.equal(splitEmail('Subject: S\r\nPreview text: P\r\n\r\nBody')?.body, 'Body');
});

test('returns null for anything that is not a labelled email', () => {
  assert.equal(splitEmail('Hi Anna, quick question about your team.'), null);
  assert.equal(splitEmail('Subject: only a subject\n\nBody'), null);
  assert.equal(splitEmail('Subject: S\nPreview text: P\n\n'), null);
});
