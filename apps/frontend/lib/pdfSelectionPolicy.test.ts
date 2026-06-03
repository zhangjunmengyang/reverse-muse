import assert from 'node:assert/strict';

import { shouldForwardPdfSelection } from './pdfSelectionPolicy';

function test(name: string, fn: () => void) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

test('forwards compact selections when configured threshold allows them', () => {
  assert.equal(shouldForwardPdfSelection('attention', 6), true);
});

test('still ignores tiny accidental selections', () => {
  assert.equal(shouldForwardPdfSelection('a', 6), false);
});
