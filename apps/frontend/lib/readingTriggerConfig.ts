export interface ReadingTriggerConfig {
  initialGraceMs: number;
  observingMs: number;
  denseTextDwellMs: number;
  normalTextMinDwellMs: number;
  normalTextMaxDwellMs: number;
  normalTextReadingRatio: number;
  wordReadingMs: number;
  charReadingMs: number;
  globalCooldownMs: number;
  sameTextCooldownMs: number;
  backtrackPauseMs: number;
  backtrackDistancePx: number;
  mouseMoveThresholdPx: number;
  scrollActivityThresholdPx: number;
  highSignalMinChars: number;
  minLetterRatio: number;
  selectionDelayMs: number;
  selectionMinChars: number;
  technicalSelectionMinChars: number;
}

export const READING_TRIGGER_CONFIG_STORAGE_KEY = 'reverse-muse:reading-trigger-config';
export const READING_TRIGGER_CONFIG_EVENT = 'reverse-muse:reading-trigger-config-change';

export const DEFAULT_READING_TRIGGER_CONFIG: ReadingTriggerConfig = {
  initialGraceMs: 4_000,
  observingMs: 2_500,
  denseTextDwellMs: 4_500,
  normalTextMinDwellMs: 5_200,
  normalTextMaxDwellMs: 8_500,
  normalTextReadingRatio: 0.55,
  wordReadingMs: 280,
  charReadingMs: 45,
  globalCooldownMs: 18_000,
  sameTextCooldownMs: 75_000,
  backtrackPauseMs: 1_800,
  backtrackDistancePx: 260,
  mouseMoveThresholdPx: 50,
  scrollActivityThresholdPx: 30,
  highSignalMinChars: 45,
  minLetterRatio: 0.45,
  selectionDelayMs: 700,
  selectionMinChars: 12,
  technicalSelectionMinChars: 6,
};

const LIMITS: Record<keyof ReadingTriggerConfig, [number, number]> = {
  initialGraceMs: [0, 20_000],
  observingMs: [500, 10_000],
  denseTextDwellMs: [1_000, 20_000],
  normalTextMinDwellMs: [1_000, 30_000],
  normalTextMaxDwellMs: [2_000, 45_000],
  normalTextReadingRatio: [0.1, 2],
  wordReadingMs: [80, 1_200],
  charReadingMs: [10, 220],
  globalCooldownMs: [0, 120_000],
  sameTextCooldownMs: [0, 300_000],
  backtrackPauseMs: [300, 15_000],
  backtrackDistancePx: [40, 1_500],
  mouseMoveThresholdPx: [5, 300],
  scrollActivityThresholdPx: [5, 300],
  highSignalMinChars: [10, 300],
  minLetterRatio: [0, 1],
  selectionDelayMs: [0, 5_000],
  selectionMinChars: [1, 120],
  technicalSelectionMinChars: [1, 80],
};

function clamp(value: number, [min, max]: [number, number]): number {
  return Math.min(Math.max(value, min), max);
}

export function normalizeReadingTriggerConfig(
  value: Partial<ReadingTriggerConfig> | null | undefined
): ReadingTriggerConfig {
  const merged = {
    ...DEFAULT_READING_TRIGGER_CONFIG,
    ...(value || {}),
  };

  const normalized = { ...DEFAULT_READING_TRIGGER_CONFIG };
  for (const key of Object.keys(normalized) as Array<keyof ReadingTriggerConfig>) {
    const nextValue = Number(merged[key]);
    normalized[key] = Number.isFinite(nextValue)
      ? clamp(nextValue, LIMITS[key])
      : DEFAULT_READING_TRIGGER_CONFIG[key];
  }

  if (normalized.normalTextMaxDwellMs < normalized.normalTextMinDwellMs) {
    normalized.normalTextMaxDwellMs = normalized.normalTextMinDwellMs;
  }

  if (normalized.selectionMinChars < normalized.technicalSelectionMinChars) {
    normalized.selectionMinChars = normalized.technicalSelectionMinChars;
  }

  return normalized;
}

export function readStoredReadingTriggerConfig(): ReadingTriggerConfig {
  if (typeof window === 'undefined') {
    return DEFAULT_READING_TRIGGER_CONFIG;
  }

  const stored = window.localStorage.getItem(READING_TRIGGER_CONFIG_STORAGE_KEY);
  if (!stored) {
    return DEFAULT_READING_TRIGGER_CONFIG;
  }

  try {
    return normalizeReadingTriggerConfig(JSON.parse(stored));
  } catch {
    return DEFAULT_READING_TRIGGER_CONFIG;
  }
}

export function saveStoredReadingTriggerConfig(config: ReadingTriggerConfig): ReadingTriggerConfig {
  const normalized = normalizeReadingTriggerConfig(config);
  window.localStorage.setItem(
    READING_TRIGGER_CONFIG_STORAGE_KEY,
    JSON.stringify(normalized)
  );
  window.dispatchEvent(new CustomEvent(READING_TRIGGER_CONFIG_EVENT, {
    detail: normalized,
  }));
  return normalized;
}

export function resetStoredReadingTriggerConfig(): ReadingTriggerConfig {
  window.localStorage.removeItem(READING_TRIGGER_CONFIG_STORAGE_KEY);
  window.dispatchEvent(new CustomEvent(READING_TRIGGER_CONFIG_EVENT, {
    detail: DEFAULT_READING_TRIGGER_CONFIG,
  }));
  return DEFAULT_READING_TRIGGER_CONFIG;
}
