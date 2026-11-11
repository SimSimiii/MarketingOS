import assert from 'node:assert/strict';
import { test } from 'node:test';
import { contrast, emailColours } from '../src/lib/email-colour.ts';

// What backend/app/marketing/render_html.py's BrandStyle answers for the same
// colours. The preview is only worth looking at if it draws what is sent.
const RENDERER = {
  '#1a56db': { accent: '#1a56db', fill: '#1a56db', onFill: '#ffffff' },
  '#ff6a00': { accent: '#c75300', fill: '#ff6a00', onFill: '#14161a' },
  '#ffd400': { accent: '#8a7200', fill: '#ffd400', onFill: '#14161a' },
  '#faf7f0': { accent: '#8e712f', fill: '#8e712f', onFill: '#ffffff' },
  '#ffd1dc': { accent: '#ea0038', fill: '#ffd1dc', onFill: '#14161a' },
  '#000000': { accent: '#000000', fill: '#000000', onFill: '#ffffff' },
};

test('draws every colour the way the email renderer does', () => {
  for (const [colour, expected] of Object.entries(RENDERER)) {
    assert.deepEqual(emailColours(colour), expected, colour);
  }
});

test('a pale brand colour keeps its button and gets readable text', () => {
  const { accent, fill, onFill } = emailColours('#ffd400');
  assert.equal(fill, '#ffd400');
  assert.ok(contrast(accent, '#ffffff') >= 4.5);
  assert.ok(contrast(fill, onFill) >= 4.5);
});

test('anything that is not a hex falls back to the default blue', () => {
  assert.deepEqual(emailColours(''), emailColours('#1a56db'));
  assert.deepEqual(emailColours('blue'), emailColours('#1a56db'));
  assert.deepEqual(emailColours('#ABC'), emailColours('#aabbcc'));
});
