import { ApiClientError } from './client';

export function errorMessage(err: unknown): string {
  if (err instanceof ApiClientError) return err.message;
  if (err instanceof Error) return err.message;
  return '未知错误';
}

export function errorHint(err: unknown): string | undefined {
  if (err instanceof ApiClientError) return err.hint || undefined;
  return undefined;
}