import { describe, expect, it } from 'vitest';
import { fmtDateTime, fmtDuration, fmtPercent, fmtTokens, shortId, truncate } from '../src/lib/utils/format';

describe('format utils', () => {
  it('formats datetime in local time', () => {
    expect(fmtDateTime('2026-01-02T03:04:05+08:00')).toBe('2026-01-02 03:04');
  });

  it('returns dash for empty datetime', () => {
    expect(fmtDateTime(null)).toBe('—');
  });

  it('formats duration with minutes', () => {
    expect(fmtDuration(95)).toBe('1m35s');
    expect(fmtDuration(42)).toBe('42s');
  });

  it('formats percentage with one decimal', () => {
    expect(fmtPercent(0.1234)).toBe('12.3%');
  });

  it('shortens large token counts', () => {
    expect(fmtTokens(999)).toBe('999');
    expect(fmtTokens(1500)).toBe('1.5k');
  });

  it('shortens ids and truncates text', () => {
    expect(shortId('abcdefghijklmnop')).toBe('abcdefgh…mnop');
    expect(truncate('x'.repeat(200)).length).toBeLessThan(200);
  });
});