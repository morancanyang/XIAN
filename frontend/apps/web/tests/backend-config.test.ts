import { beforeEach, describe, expect, it } from 'vitest';
import {
  apiBase,
  getBackendBase,
  isRemoteBackend,
  normalizeBase,
  setBackendBase,
  wsOrigin
} from '../src/lib/config/backend';

describe('backend config', () => {
  beforeEach(() => {
    window.localStorage.clear();
    setBackendBase('');
    window.localStorage.clear();
  });

  it('normalises trailing slashes and blanks', () => {
    expect(normalizeBase('http://1.2.3.4:8000/')).toBe('http://1.2.3.4:8000');
    expect(normalizeBase('http://1.2.3.4:8000///')).toBe('http://1.2.3.4:8000');
    expect(normalizeBase('')).toBe('');
    expect(normalizeBase('   ')).toBe('');
    expect(normalizeBase('/')).toBe('');
  });

  it('defaults to same-origin when unset', () => {
    expect(getBackendBase()).toBe('');
    expect(apiBase()).toBe('/api');
    expect(wsOrigin()).toBeNull();
    expect(isRemoteBackend()).toBe(false);
  });

  it('persists a remote backend and derives api prefix', () => {
    setBackendBase('http://192.168.1.5:8000/');
    expect(getBackendBase()).toBe('http://192.168.1.5:8000');
    expect(apiBase()).toBe('http://192.168.1.5:8000/api');
    expect(isRemoteBackend()).toBe(true);
  });

  it('derives ws origin, upgrading https to wss', () => {
    setBackendBase('http://192.168.1.5:8000');
    expect(wsOrigin()).toBe('ws://192.168.1.5:8000');

    setBackendBase('https://xian.example.com');
    expect(wsOrigin()).toBe('wss://xian.example.com');
  });

  it('survives an unparsable value without throwing', () => {
    setBackendBase('not a url');
    expect(wsOrigin()).toBeNull();
    expect(apiBase()).toBe('not a url/api');
  });
});
