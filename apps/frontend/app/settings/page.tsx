'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  BookOpen,
  Gauge,
  RotateCcw,
  SlidersHorizontal,
  Sparkles,
} from 'lucide-react';

import {
  DEFAULT_READING_TRIGGER_CONFIG,
  normalizeReadingTriggerConfig,
  readStoredReadingTriggerConfig,
  resetStoredReadingTriggerConfig,
  saveStoredReadingTriggerConfig,
  type ReadingTriggerConfig,
} from '@/lib/readingTriggerConfig';

type ConfigKey = keyof ReadingTriggerConfig;
type PresetKey = 'active' | 'balanced' | 'quiet';

interface TriggerControl {
  key: ConfigKey;
  label: string;
  detail: string;
  min: number;
  max: number;
  step: number;
  unit: string;
  format?: (value: number) => string;
}

interface TriggerGroup {
  title: string;
  accent: string;
  controls: TriggerControl[];
}

interface TriggerPreset {
  key: PresetKey;
  label: string;
  detail: string;
  config: ReadingTriggerConfig;
}

const formatMs = (value: number) => `${(value / 1000).toFixed(1)}s`;
const formatPx = (value: number) => `${Math.round(value)}px`;
const formatChars = (value: number) => `${Math.round(value)} chars`;
const formatRatio = (value: number) => `${Math.round(value * 100)}%`;

const PRESETS: TriggerPreset[] = [
  {
    key: 'active',
    label: 'Active',
    detail: 'Fast intervention',
    config: DEFAULT_READING_TRIGGER_CONFIG,
  },
  {
    key: 'balanced',
    label: 'Balanced',
    detail: 'Fewer repeats',
    config: normalizeReadingTriggerConfig({
      ...DEFAULT_READING_TRIGGER_CONFIG,
      observingMs: 3_200,
      denseTextDwellMs: 5_200,
      normalTextMinDwellMs: 6_500,
      normalTextMaxDwellMs: 10_000,
      globalCooldownMs: 28_000,
      sameTextCooldownMs: 100_000,
      selectionDelayMs: 900,
      selectionMinChars: 16,
    }),
  },
  {
    key: 'quiet',
    label: 'Quiet',
    detail: 'Only strong signals',
    config: normalizeReadingTriggerConfig({
      ...DEFAULT_READING_TRIGGER_CONFIG,
      initialGraceMs: 6_000,
      observingMs: 4_000,
      denseTextDwellMs: 7_000,
      normalTextMinDwellMs: 9_000,
      normalTextMaxDwellMs: 14_000,
      globalCooldownMs: 45_000,
      sameTextCooldownMs: 150_000,
      backtrackPauseMs: 2_800,
      backtrackDistancePx: 380,
      highSignalMinChars: 70,
      selectionDelayMs: 1_200,
      selectionMinChars: 24,
    }),
  },
];

const GROUPS: TriggerGroup[] = [
  {
    title: 'Dwell',
    accent: 'var(--accent-secondary)',
    controls: [
      {
        key: 'observingMs',
        label: 'Observation entry',
        detail: 'Idle time before the orb enters observing state.',
        min: 500,
        max: 10_000,
        step: 100,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'initialGraceMs',
        label: 'Paper-load grace',
        detail: 'Silence window after a paper is opened.',
        min: 0,
        max: 20_000,
        step: 250,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'denseTextDwellMs',
        label: 'Dense text dwell',
        detail: 'Dwell needed for technical paragraphs.',
        min: 1_000,
        max: 20_000,
        step: 250,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'normalTextMinDwellMs',
        label: 'Normal dwell floor',
        detail: 'Minimum dwell for ordinary paragraphs.',
        min: 1_000,
        max: 30_000,
        step: 250,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'normalTextMaxDwellMs',
        label: 'Normal dwell ceiling',
        detail: 'Maximum dwell for long ordinary paragraphs.',
        min: 2_000,
        max: 45_000,
        step: 250,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'normalTextReadingRatio',
        label: 'Reading ratio',
        detail: 'How much estimated reading time should pass.',
        min: 0.1,
        max: 2,
        step: 0.05,
        unit: 'ratio',
        format: formatRatio,
      },
    ],
  },
  {
    title: 'Backtrack',
    accent: 'var(--warning)',
    controls: [
      {
        key: 'backtrackDistancePx',
        label: 'Backtrack distance',
        detail: 'Upward scroll distance treated as rereading.',
        min: 40,
        max: 1_500,
        step: 10,
        unit: 'px',
        format: formatPx,
      },
      {
        key: 'backtrackPauseMs',
        label: 'Backtrack pause',
        detail: 'Rest time after scrolling upward.',
        min: 300,
        max: 15_000,
        step: 100,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'scrollActivityThresholdPx',
        label: 'Scroll activity',
        detail: 'Scroll delta that resets the idle timer.',
        min: 5,
        max: 300,
        step: 5,
        unit: 'px',
        format: formatPx,
      },
    ],
  },
  {
    title: 'Cooldown',
    accent: 'var(--success)',
    controls: [
      {
        key: 'globalCooldownMs',
        label: 'Global cooldown',
        detail: 'Minimum gap between passive insights.',
        min: 0,
        max: 120_000,
        step: 1_000,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'sameTextCooldownMs',
        label: 'Same text cooldown',
        detail: 'Repeat suppression for the same visible text.',
        min: 0,
        max: 300_000,
        step: 1_000,
        unit: 'ms',
        format: formatMs,
      },
    ],
  },
  {
    title: 'Text Signals',
    accent: 'var(--error)',
    controls: [
      {
        key: 'highSignalMinChars',
        label: 'Visible text minimum',
        detail: 'Minimum visible text length for passive triggers.',
        min: 10,
        max: 300,
        step: 1,
        unit: 'chars',
        format: formatChars,
      },
      {
        key: 'minLetterRatio',
        label: 'Letter ratio',
        detail: 'Minimum letter density for visible text.',
        min: 0,
        max: 1,
        step: 0.05,
        unit: 'ratio',
        format: formatRatio,
      },
      {
        key: 'wordReadingMs',
        label: 'Word reading speed',
        detail: 'Estimated reading time per word.',
        min: 80,
        max: 1_200,
        step: 10,
        unit: 'ms',
        format: value => `${Math.round(value)}ms`,
      },
      {
        key: 'charReadingMs',
        label: 'Character reading speed',
        detail: 'Estimated reading time per character.',
        min: 10,
        max: 220,
        step: 5,
        unit: 'ms',
        format: value => `${Math.round(value)}ms`,
      },
    ],
  },
  {
    title: 'Selection',
    accent: 'var(--accent-primary)',
    controls: [
      {
        key: 'selectionDelayMs',
        label: 'Selection delay',
        detail: 'Wait after selection before intervening.',
        min: 0,
        max: 5_000,
        step: 100,
        unit: 'ms',
        format: formatMs,
      },
      {
        key: 'selectionMinChars',
        label: 'Selection minimum',
        detail: 'Ordinary selected text length.',
        min: 1,
        max: 120,
        step: 1,
        unit: 'chars',
        format: formatChars,
      },
      {
        key: 'technicalSelectionMinChars',
        label: 'Technical selection minimum',
        detail: 'Compact technical selection length.',
        min: 1,
        max: 80,
        step: 1,
        unit: 'chars',
        format: formatChars,
      },
      {
        key: 'mouseMoveThresholdPx',
        label: 'Mouse activity',
        detail: 'Pointer movement that resets idle time.',
        min: 5,
        max: 300,
        step: 5,
        unit: 'px',
        format: formatPx,
      },
    ],
  },
];

export default function TriggerSettingsPage() {
  const [config, setConfig] = useState<ReadingTriggerConfig>(
    DEFAULT_READING_TRIGGER_CONFIG
  );
  const [appliedPreset, setAppliedPreset] = useState<PresetKey | null>('active');

  useEffect(() => {
    const stored = readStoredReadingTriggerConfig();
    setConfig(stored);
    setAppliedPreset(findPreset(stored));
  }, []);

  const activeSummary = useMemo(() => {
    const passiveSeconds = (config.denseTextDwellMs / 1000).toFixed(1);
    const cooldownSeconds = (config.globalCooldownMs / 1000).toFixed(0);
    return `${passiveSeconds}s dense dwell / ${cooldownSeconds}s cooldown`;
  }, [config.denseTextDwellMs, config.globalCooldownMs]);

  const updateConfigValue = (key: ConfigKey, value: number) => {
    const next = saveStoredReadingTriggerConfig({
      ...config,
      [key]: value,
    });
    setConfig(next);
    setAppliedPreset(findPreset(next));
  };

  const applyPreset = (preset: TriggerPreset) => {
    const next = saveStoredReadingTriggerConfig(preset.config);
    setConfig(next);
    setAppliedPreset(preset.key);
  };

  const resetConfig = () => {
    const next = resetStoredReadingTriggerConfig();
    setConfig(next);
    setAppliedPreset('active');
  };

  return (
    <main className="min-h-screen bg-[var(--bg-primary)]">
      <header className="sticky top-0 z-20 border-b border-white/5 bg-[var(--bg-primary)]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              href="/reading"
              className="tooltip flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg border border-[var(--ghost-border)] text-[var(--text-muted)] transition-colors hover:border-[var(--accent-primary)] hover:bg-[var(--ghost-bg)] hover:text-[var(--text-primary)]"
              data-tooltip="Back to reading"
              aria-label="Back to reading"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg border border-[var(--ghost-border)] bg-[var(--ghost-bg)]">
              <SlidersHorizontal className="h-4 w-4 text-[var(--accent-secondary)]" />
            </div>
            <div className="min-w-0">
              <h1 className="font-display text-xl font-semibold text-[var(--text-primary)]">
                Trigger Tuning
              </h1>
              <p className="truncate text-xs text-[var(--text-muted)]">
                {activeSummary}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link href="/reading" className="btn btn-ghost hidden text-sm sm:inline-flex">
              <BookOpen className="h-4 w-4" />
              <span>Reading</span>
            </Link>
            <button onClick={resetConfig} className="btn btn-ghost text-sm">
              <RotateCcw className="h-4 w-4" />
              <span>Reset</span>
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-6xl gap-5 px-5 py-6 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-4">
          <section className="rounded-lg border border-white/5 bg-[var(--bg-secondary)] p-4">
            <div className="mb-3 flex items-center gap-2">
              <Gauge className="h-4 w-4 text-[var(--accent-secondary)]" />
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Presets
              </h2>
            </div>
            <div className="space-y-2">
              {PRESETS.map(preset => (
                <button
                  key={preset.key}
                  onClick={() => applyPreset(preset)}
                  className={`
                    flex w-full items-center justify-between rounded-lg border px-3 py-2 text-left transition-colors
                    ${appliedPreset === preset.key
                      ? 'border-[var(--accent-primary)] bg-[var(--ghost-bg)] text-[var(--text-primary)]'
                      : 'border-white/5 bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:border-[var(--ghost-border)] hover:text-[var(--text-primary)]'
                    }
                  `}
                >
                  <span>
                    <span className="block text-sm font-medium">{preset.label}</span>
                    <span className="block text-xs text-[var(--text-muted)]">
                      {preset.detail}
                    </span>
                  </span>
                  {appliedPreset === preset.key && (
                    <Sparkles className="h-4 w-4 flex-shrink-0 text-[var(--accent-secondary)]" />
                  )}
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-white/5 bg-[var(--bg-secondary)] p-4">
            <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">
              Current Bias
            </h2>
            <div className="space-y-3 text-sm">
              <MetricRow
                label="Passive first signal"
                value={formatMs(config.denseTextDwellMs)}
              />
              <MetricRow
                label="Backtrack pause"
                value={formatMs(config.backtrackPauseMs)}
              />
              <MetricRow
                label="Selection delay"
                value={formatMs(config.selectionDelayMs)}
              />
              <MetricRow
                label="Same text mute"
                value={formatMs(config.sameTextCooldownMs)}
              />
            </div>
          </section>
        </aside>

        <div className="space-y-5">
          {GROUPS.map(group => (
            <section
              key={group.title}
              className="rounded-lg border border-white/5 bg-[var(--bg-secondary)]"
            >
              <div
                className="flex items-center justify-between border-b border-white/5 px-4 py-3"
                style={{ borderTop: `2px solid ${group.accent}` }}
              >
                <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                  {group.title}
                </h2>
              </div>
              <div className="divide-y divide-white/5">
                {group.controls.map(control => (
                  <NumberControl
                    key={control.key}
                    control={control}
                    value={config[control.key]}
                    onChange={value => updateConfigValue(control.key, value)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}

function NumberControl({
  control,
  value,
  onChange,
}: {
  control: TriggerControl;
  value: number;
  onChange: (value: number) => void;
}) {
  const displayValue = control.format ? control.format(value) : String(value);

  return (
    <div className="grid gap-3 px-4 py-4 md:grid-cols-[minmax(180px,1fr)_minmax(280px,1.1fr)] md:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <label
            htmlFor={`trigger-${control.key}`}
            className="text-sm font-medium text-[var(--text-primary)]"
          >
            {control.label}
          </label>
          <span className="font-mono text-xs text-[var(--accent-secondary)]">
            {displayValue}
          </span>
        </div>
        <p className="mt-1 text-xs text-[var(--text-muted)]">
          {control.detail}
        </p>
      </div>

      <div className="grid gap-2 sm:grid-cols-[1fr_120px] sm:items-center">
        <input
          id={`trigger-${control.key}`}
          type="range"
          min={control.min}
          max={control.max}
          step={control.step}
          value={value}
          onChange={event => onChange(Number(event.target.value))}
          className="h-2 w-full cursor-pointer accent-[var(--accent-primary)]"
        />
        <div className="flex items-center rounded-lg border border-white/10 bg-[var(--bg-tertiary)] px-2 py-1.5">
          <input
            type="number"
            min={control.min}
            max={control.max}
            step={control.step}
            value={value}
            onChange={event => onChange(Number(event.target.value))}
            className="w-full bg-transparent text-right font-mono text-xs text-[var(--text-primary)] outline-none"
            aria-label={`${control.label} value`}
          />
          <span className="ml-2 flex-shrink-0 text-[10px] text-[var(--text-muted)]">
            {control.unit}
          </span>
        </div>
      </div>
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-[var(--text-muted)]">{label}</span>
      <span className="font-mono text-xs text-[var(--text-primary)]">{value}</span>
    </div>
  );
}

function findPreset(config: ReadingTriggerConfig): PresetKey | null {
  const keys = Object.keys(DEFAULT_READING_TRIGGER_CONFIG) as ConfigKey[];
  const match = PRESETS.find(preset =>
    keys.every(key => preset.config[key] === config[key])
  );

  return match?.key || null;
}
