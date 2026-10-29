import assert from 'node:assert/strict';
import { test } from 'node:test';
import { activityMessage, executionReview, jobProgress, problemText, progressText } from '../src/lib/product-progress.ts';

test('historical knowledge and research receipts are hidden without changing source logs', () => {
  const lines = [
    'Reading 3 documents: what the business is',
    'Knowledge compiler · sonnet · 10.7s · 11,779 in / 551 out',
    'Audience cartographer · future-model · 8.0s · 20,000 in / 500 out · $0.0500',
    'Knowledge compiler · step completed',
    'Knowledge compiled: 12 facts, 3 segments, 2 gaps',
  ];
  assert.deepEqual(jobProgress(lines), [lines[0], lines[4]]);
  assert.equal(lines.length, 5);
});

test('both replayed and live transport events are hidden even with unknown model names', () => {
  for (const type of ['model_call_started', 'model_call_finished']) {
    const base = { level: 'info', agent_id: 'email_writer', message: 'secret-model · 123 in / 456 out' };
    assert.equal(activityMessage({ ...base, type }), null);
    assert.equal(activityMessage({ ...base, event_type: type }), null);
  }
  assert.equal(activityMessage({ level: 'debug', agent_id: null, message: 'Full internal prompt' }), null);
});

test('retries remain visible and completed steps never echo raw receipts', () => {
  const base = { level: 'warning', agent_id: 'email_writer', message: 'secret-model did not answer' };
  assert.equal(activityMessage({ ...base, type: 'model_call_retried' }), 'This step was interrupted. Retrying automatically…');
  assert.equal(activityMessage({ ...base, type: 'agent_completed' }), 'Writing the email · complete');
});

test('product facts and actionable usage problems remain available', () => {
  const message = 'Email 2 needs a stronger explanation of the client intake form.';
  assert.equal(activityMessage({ type: 'critique', level: 'info', agent_id: 'conversion_critic', message }), message);
  assert.equal(progressText('Claude integration is included in this product.'), 'Claude integration is included in this product.');
  assert.deepEqual(jobProgress(['Reading OpenAI product pages.']), ['Reading OpenAI product pages.']);
  assert.equal(problemText('Sources changed during compilation. Please compile again.'), 'Sources changed during compilation. Please compile again.');
  assert.equal(problemText('Insufficient credits.'), 'Insufficient credits.');
  assert.doesNotMatch(problemText('OpenAI ProviderError: gpt-future timed out'), /OpenAI|ProviderError|gpt-future/);
  assert.equal(progressText('sonnet answered with 551 characters in 10.7s (11,779 in / 551 out)', 'Writing the email…'), 'Writing the email…');
});

test('historical audience reaction estimates are replaced without changing product prices', () => {
  assert.equal(progressText('Written to repair shops - 75% of them are estimated to bite'),
    'Written to repair shops — selected audience hypothesis; response is unmeasured');
  assert.equal(progressText('Save 20% on the annual plan.'), 'Save 20% on the annual plan.');
});


test('delivery warnings survive a completed process or legacy missing run_status', () => {
  const result = { report: { delivered: 1, promised: 1, emails: [{ clean: true, landed: false }] } };
  const review = executionReview('completed', result, null);
  assert.equal(review.needsReview, true);
  assert.equal(review.label, 'Drafts need review');
  assert.ok(review.reasons.length);
  const strategy = executionReview('completed', { report: { emails: [{ clean: true, unresolved: ['Argument needs review'] }] } }, null);
  assert.ok(strategy.reasons.some(reason => reason.includes('strategy or review')));
  assert.ok(strategy.reasons.every(reason => !reason.includes('automatic')));
  assert.equal(executionReview('running', result, null).needsReview, false);
  assert.equal(executionReview('completed', { report: { delivered: 1, promised: 2 } }, null).label, 'Partial delivery');
  assert.equal(executionReview('completed', { report: { delivered: 1, promised: 1, emails: [{ landed: true, clean: true }] } }, null).needsReview, false);
});
