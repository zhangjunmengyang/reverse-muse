import {
  DEFAULT_READING_TRIGGER_CONFIG,
  type ReadingTriggerConfig,
} from './readingTriggerConfig';

export type PassiveTriggerType = 'linger' | 'backtrack';

export type TriggerDecisionReason =
  | 'dense_text_dwell'
  | 'normal_text_dwell'
  | 'backtrack_pause'
  | 'initial_grace'
  | 'low_signal_text'
  | 'global_cooldown'
  | 'same_text_cooldown'
  | 'insufficient_dwell';

export interface ReadingTriggerInput {
  now: number;
  paperLoadedAt: number;
  idleMs: number;
  visibleText: string;
  scrollTop: number;
  backtrackDistancePx: number;
  lastTriggerAt: number;
  lastTriggerByText: Record<string, number>;
  config?: ReadingTriggerConfig;
}

export interface ReadingTriggerDecision {
  shouldTrigger: boolean;
  reason: TriggerDecisionReason;
  triggerType?: PassiveTriggerType;
  text: string;
  textSignature: string;
  minIdleMs: number;
}

const TECHNICAL_PATTERNS = [
  /\b(transformer|attention|embedding|diffusion|llm|rag|agent|token|context|gradient)\b/i,
  /\b(model|algorithm|architecture|benchmark|dataset|training|inference|retrieval)\b/i,
  /[A-Z]{2,}|\d+\.\d+|[=≈≤≥∑∏√]/,
  /\([^)]{8,}\)/,
];

export function normalizeReadingText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

export function createTextSignature(text: string): string {
  return normalizeReadingText(text).toLowerCase().slice(0, 180);
}

export function isHighSignalText(
  text: string,
  config: ReadingTriggerConfig = DEFAULT_READING_TRIGGER_CONFIG
): boolean {
  return isHighSignalTextWithConfig(text, config);
}

export function isHighSignalTextWithConfig(
  text: string,
  config: ReadingTriggerConfig
): boolean {
  const normalized = normalizeReadingText(text);
  if (normalized.length < config.highSignalMinChars) {
    return false;
  }

  const letterCount = (normalized.match(/[A-Za-z\u4e00-\u9fff]/g) || []).length;
  if (letterCount / normalized.length < config.minLetterRatio) {
    return false;
  }

  if (/^(references|bibliography|acknowledg(e)?ments)\b/i.test(normalized)) {
    return false;
  }

  return true;
}

export function isDenseOrTechnicalText(text: string): boolean {
  const normalized = normalizeReadingText(text);
  return TECHNICAL_PATTERNS.some(pattern => pattern.test(normalized));
}

export function shouldConsiderSelectionInsight(
  text: string,
  config: ReadingTriggerConfig = DEFAULT_READING_TRIGGER_CONFIG
): boolean {
  return shouldConsiderSelectionInsightWithConfig(text, config);
}

export function shouldConsiderSelectionInsightWithConfig(
  text: string,
  config: ReadingTriggerConfig
): boolean {
  const normalized = normalizeReadingText(text);
  if (normalized.length < config.technicalSelectionMinChars) {
    return false;
  }

  if (normalized.length >= config.selectionMinChars) {
    return true;
  }

  return isDenseOrTechnicalText(normalized);
}

export function estimateDwellMs(
  text: string,
  config: ReadingTriggerConfig = DEFAULT_READING_TRIGGER_CONFIG
): number {
  return estimateDwellMsWithConfig(text, config);
}

export function estimateDwellMsWithConfig(
  text: string,
  config: ReadingTriggerConfig
): number {
  const normalized = normalizeReadingText(text);
  if (isDenseOrTechnicalText(normalized)) {
    return config.denseTextDwellMs;
  }

  const wordCount = normalized.split(/\s+/).filter(Boolean).length;
  const charCount = normalized.length;
  const estimatedReadingMs = Math.max(
    wordCount * config.wordReadingMs,
    charCount * config.charReadingMs
  );

  return Math.min(
    Math.max(
      estimatedReadingMs * config.normalTextReadingRatio,
      config.normalTextMinDwellMs
    ),
    config.normalTextMaxDwellMs
  );
}

export function decideReadingTrigger(input: ReadingTriggerInput): ReadingTriggerDecision {
  const config = input.config || DEFAULT_READING_TRIGGER_CONFIG;
  const text = normalizeReadingText(input.visibleText);
  const textSignature = createTextSignature(text);
  const minIdleMs = estimateDwellMsWithConfig(text, config);
  const baseDecision = {
    text,
    textSignature,
    minIdleMs,
  };

  if (!isHighSignalTextWithConfig(text, config)) {
    return { ...baseDecision, shouldTrigger: false, reason: 'low_signal_text' };
  }

  if (input.now - input.paperLoadedAt < config.initialGraceMs) {
    return { ...baseDecision, shouldTrigger: false, reason: 'initial_grace' };
  }

  if (input.lastTriggerAt && input.now - input.lastTriggerAt < config.globalCooldownMs) {
    return { ...baseDecision, shouldTrigger: false, reason: 'global_cooldown' };
  }

  const sameTextTriggeredAt = input.lastTriggerByText[textSignature];
  if (
    sameTextTriggeredAt
    && input.now - sameTextTriggeredAt < config.sameTextCooldownMs
  ) {
    return { ...baseDecision, shouldTrigger: false, reason: 'same_text_cooldown' };
  }

  if (
    input.backtrackDistancePx >= config.backtrackDistancePx
    && input.idleMs >= config.backtrackPauseMs
  ) {
    return {
      ...baseDecision,
      shouldTrigger: true,
      triggerType: 'backtrack',
      reason: 'backtrack_pause',
    };
  }

  if (input.idleMs >= minIdleMs) {
    return {
      ...baseDecision,
      shouldTrigger: true,
      triggerType: 'linger',
      reason: isDenseOrTechnicalText(text) ? 'dense_text_dwell' : 'normal_text_dwell',
    };
  }

  return { ...baseDecision, shouldTrigger: false, reason: 'insufficient_dwell' };
}
