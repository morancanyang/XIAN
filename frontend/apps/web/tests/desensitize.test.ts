import { describe, expect, it } from 'vitest';
import { desensitize, maskCanaryValue } from '../src/lib/utils/desensitize';

describe('desensitize', () => {
  it('passes through when level is none', () => {
    expect(desensitize('mail me at a@b.com', 'none')).toBe('mail me at a@b.com');
  });

  it('masks canary keys in partial mode', () => {
    const out = desensitize('payload sk-canary-abc123def456 end', 'partial');
    expect(out).toContain('sk-canary');
    expect(out).toContain('****');
    expect(out).not.toContain('sk-canary-abc123def456');
  });

  it('masks phone and id card', () => {
    expect(desensitize('call 13800138000', 'partial')).toBe('call 138****8000');
    expect(desensitize('id 110101199003077758', 'full')).toBe('id 110101********7758');
  });

  it('never returns the raw canary value from maskCanaryValue', () => {
    expect(maskCanaryValue('sk-canary-topsecret')).not.toContain('topsecret');
  });
});