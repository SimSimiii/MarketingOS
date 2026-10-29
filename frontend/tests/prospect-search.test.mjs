import assert from 'node:assert/strict';
import { test } from 'node:test';
import { prospectSearchRequest } from '../src/lib/prospect-search.ts';

// Synthetic audience; no organisation or person described here is real.
const segment = {
  name: 'Synthetic repair teams',
  signals: ['Published warranty workflow', 'Maintenance announcement'],
};
const filters = {
  target: 'people', source: 'linkedin', query: '  Workshop owners  ',
  roles: 'Owner, Operations lead, Owner', industries: 'Repair',
  companySizes: '10–50 employees', geographies: 'France, Belgium',
  languages: 'French', signals: 'Profile names workshop role',
  exclusions: 'Job seekers', limit: 4,
};

test('edited prospect filters and audience association reach the saved search request', () => {
  const request = prospectSearchRequest(segment, filters);
  assert.equal(request.segment_name, segment.name);
  assert.equal(request.source, 'linkedin');
  assert.equal(request.target, 'people');
  assert.equal(request.query, 'Workshop owners');
  assert.equal(request.limit, 4);
  assert.deepEqual(request.criteria.roles, ['Owner', 'Operations lead']);
  assert.deepEqual(request.criteria.company_sizes, ['10–50 employees']);
  assert.deepEqual(request.criteria.languages, ['French']);
  assert.deepEqual(request.criteria.geographies, ['France', 'Belgium']);
  assert.deepEqual(request.criteria.profile_signals, ['Profile names workshop role']);
  assert.deepEqual(request.criteria.corroboration, segment.signals);
  assert.deepEqual(request.criteria.exclusions, ['Job seekers']);
});

test('consumer search uses public reach channels and clears professional-only filters', () => {
  const request = prospectSearchRequest({ ...segment, name: 'Synthetic home renovators' }, {
    ...filters, target: 'venues', source: 'linkedin', query: '',
  });
  assert.equal(request.source, 'web');
  assert.equal(request.target, 'venues');
  assert.equal(request.query, 'Synthetic home renovators');
  assert.deepEqual(request.criteria.roles, []);
  assert.deepEqual(request.criteria.company_sizes, []);
  assert.deepEqual(request.criteria.corroboration, []);
  assert.deepEqual(request.criteria.languages, ['French']);
});
