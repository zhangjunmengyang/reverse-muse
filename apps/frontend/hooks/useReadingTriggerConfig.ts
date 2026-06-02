'use client';

import { useEffect, useState } from 'react';

import {
  DEFAULT_READING_TRIGGER_CONFIG,
  READING_TRIGGER_CONFIG_EVENT,
  READING_TRIGGER_CONFIG_STORAGE_KEY,
  readStoredReadingTriggerConfig,
  type ReadingTriggerConfig,
} from '@/lib/readingTriggerConfig';

export function useReadingTriggerConfig(): ReadingTriggerConfig {
  const [config, setConfig] = useState<ReadingTriggerConfig>(
    DEFAULT_READING_TRIGGER_CONFIG
  );

  useEffect(() => {
    setConfig(readStoredReadingTriggerConfig());

    const handleConfigChange = (event: Event) => {
      const detail = (event as CustomEvent<ReadingTriggerConfig>).detail;
      setConfig(detail || readStoredReadingTriggerConfig());
    };

    const handleStorage = (event: StorageEvent) => {
      if (event.key === READING_TRIGGER_CONFIG_STORAGE_KEY) {
        setConfig(readStoredReadingTriggerConfig());
      }
    };

    window.addEventListener(READING_TRIGGER_CONFIG_EVENT, handleConfigChange);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener(READING_TRIGGER_CONFIG_EVENT, handleConfigChange);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  return config;
}
