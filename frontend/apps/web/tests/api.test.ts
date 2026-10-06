import { describe, expect, it, vi, beforeEach } from 'vitest';
import { ApiClientError, buildRequestPath } from '../src/lib/api/client';

describe('api client', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  it('maps domain error code to typed error with hint', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ error: 'OwnershipNotVerified', message: '未归属校验', hint: '先在资产页校验' }), {
          status: 403,
          headers: { 'content-type': 'application/json' }
        })
      )
    );

    const { apiRequest } = await import('../src/lib/api/client');
    await expect(apiRequest('/api/v1/campaigns', { method: 'POST', body: {} })).rejects.toBeInstanceOf(ApiClientError);
  });

  it('normalises network failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('ECONNREFUSED');
      })
    );
    const { apiRequest } = await import('../src/lib/api/client');
    await expect(apiRequest('/api/v1/agents')).rejects.toMatchObject({ name: 'ApiClientError', status: 0 });
  });
});

describe('buildRequestPath', () => {
  it('appends query params and drops empties', () => {
    expect(buildRequestPath('/api/v1/agents', { page: 2, keyword: '', size: undefined })).toBe(
      '/api/v1/agents?page=2'
    );
  });

  it('returns bare path when no query', () => {
    expect(buildRequestPath('/api/v1/agents')).toBe('/api/v1/agents');
  });
});