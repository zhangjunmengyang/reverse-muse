import { normalizeReadingText } from './readingTriggerPolicy';

export function shouldForwardPdfSelection(
  text: string,
  minChars: number
): boolean {
  return normalizeReadingText(text).length >= minChars;
}
