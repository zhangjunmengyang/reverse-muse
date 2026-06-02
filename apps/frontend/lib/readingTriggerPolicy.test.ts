import assert from 'node:assert/strict';

import { DEFAULT_READING_TRIGGER_CONFIG } from './readingTriggerConfig';
import {
  decideReadingTrigger,
  estimateDwellMs,
  normalizeReadingText,
  shouldConsiderSelectionInsight,
} from './readingTriggerPolicy';

const technicalText = [
  'Transformer attention connects tokens across long contexts,',
  'which lets a reading companion infer when a paragraph is conceptually dense',
  'and worth explaining before the reader explicitly asks.',
].join(' ');

function baseInput(overrides = {}) {
  return {
    now: 20_000,
    paperLoadedAt: 0,
    idleMs: 6_000,
    visibleText: technicalText,
    scrollTop: 1_000,
    backtrackDistancePx: 0,
    lastTriggerAt: 0,
    lastTriggerByText: {},
    ...overrides,
  };
}

function test(name: string, fn: () => void) {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

test('normalizes whitespace and trims visible text', () => {
  assert.equal(normalizeReadingText('  a\n\n b\t c  '), 'a b c');
});

test('uses shorter dwell threshold for technical dense text', () => {
  assert.equal(estimateDwellMs(technicalText), 4_500);
});

test('uses custom dwell threshold from config', () => {
  const decision = decideReadingTrigger(baseInput({
    idleMs: 2_500,
    config: {
      ...DEFAULT_READING_TRIGGER_CONFIG,
      denseTextDwellMs: 2_400,
    },
  }));

  assert.equal(decision.shouldTrigger, true);
  assert.equal(decision.minIdleMs, 2_400);
});

test('actively triggers linger after a short technical dwell', () => {
  const decision = decideReadingTrigger(baseInput());

  assert.equal(decision.shouldTrigger, true);
  assert.equal(decision.triggerType, 'linger');
  assert.equal(decision.reason, 'dense_text_dwell');
});

test('prioritizes backtrack when the reader scrolls up and rests', () => {
  const decision = decideReadingTrigger(baseInput({
    idleMs: 2_200,
    backtrackDistancePx: 320,
  }));

  assert.equal(decision.shouldTrigger, true);
  assert.equal(decision.triggerType, 'backtrack');
  assert.equal(decision.reason, 'backtrack_pause');
});

test('does not trigger during the initial paper-load grace period', () => {
  const decision = decideReadingTrigger(baseInput({
    now: 3_000,
    paperLoadedAt: 0,
    idleMs: 6_000,
  }));

  assert.equal(decision.shouldTrigger, false);
  assert.equal(decision.reason, 'initial_grace');
});

test('uses custom initial grace threshold from config', () => {
  const decision = decideReadingTrigger(baseInput({
    now: 3_000,
    paperLoadedAt: 0,
    idleMs: 6_000,
    config: {
      ...DEFAULT_READING_TRIGGER_CONFIG,
      initialGraceMs: 2_000,
    },
  }));

  assert.equal(decision.shouldTrigger, true);
});

test('suppresses repeated triggers on the same visible text', () => {
  const first = decideReadingTrigger(baseInput());
  assert.equal(first.shouldTrigger, true);

  const repeated = decideReadingTrigger(baseInput({
    now: 35_000,
    lastTriggerAt: 20_000,
    lastTriggerByText: {
      [first.textSignature]: 20_000,
    },
  }));

  assert.equal(repeated.shouldTrigger, false);
  assert.equal(repeated.reason, 'global_cooldown');

  const sameParagraphLater = decideReadingTrigger(baseInput({
    now: 70_000,
    lastTriggerAt: 20_000,
    lastTriggerByText: {
      [first.textSignature]: 20_000,
    },
  }));

  assert.equal(sameParagraphLater.shouldTrigger, false);
  assert.equal(sameParagraphLater.reason, 'same_text_cooldown');
});

test('filters low-value visible text', () => {
  const decision = decideReadingTrigger(baseInput({
    visibleText: 'References 1 2 3 4',
    idleMs: 10_000,
  }));

  assert.equal(decision.shouldTrigger, false);
  assert.equal(decision.reason, 'low_signal_text');
});

test('actively considers compact technical selections', () => {
  assert.equal(shouldConsiderSelectionInsight('RAG pipeline'), true);
  assert.equal(shouldConsiderSelectionInsight('attention'), true);
});

test('uses custom selection length threshold', () => {
  assert.equal(
    shouldConsiderSelectionInsight('short note'),
    false
  );
  assert.equal(
    shouldConsiderSelectionInsight('short note', {
      ...DEFAULT_READING_TRIGGER_CONFIG,
      selectionMinChars: 8,
    }),
    true
  );
});

test('ignores tiny ordinary selections', () => {
  assert.equal(shouldConsiderSelectionInsight('the'), false);
  assert.equal(shouldConsiderSelectionInsight('page 3'), false);
});
