/**
 * 前端脱敏工具（PRD 9.2）。
 * 与后端脱敏规则保持一致：展示层兜底，导出侧由后端二次脱敏。
 */

const EMAIL_RE = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
const PHONE_RE = /(?<!\d)(1[3-9]\d)(\d{4})(\d{4})(?!\d)/g;
const ID_CARD_RE = /(?<!\d)(\d{6})(\d{8})(\d{4})(?!\d)/g;
const CANARY_KEY_RE = /sk-canary-[A-Za-z0-9_-]+/g;

export type DesensitizeLevel = 'none' | 'partial' | 'full';

export function desensitize(value: string, level: DesensitizeLevel = 'partial'): string {
  if (!value || level === 'none') return value;
  if (level === 'full') {
    return value
      .replace(CANARY_KEY_RE, 'sk-canary-****')
      .replace(EMAIL_RE, '***@***.***')
      .replace(PHONE_RE, '$1****$3')
      .replace(ID_CARD_RE, '$1********$3');
  }
  return value
    .replace(CANARY_KEY_RE, (m) => `${m.slice(0, 12)}****`)
    .replace(EMAIL_RE, (m) => `${m.slice(0, 2)}****${m.slice(m.indexOf('@'))}`)
    .replace(PHONE_RE, '$1****$3')
    .replace(ID_CARD_RE, '$1********$3');
}

/** 蜜标只展示类型，不展示值（PRD 3.1.5.6）。 */
export function maskCanaryValue(value: string): string {
  if (value.startsWith('{{')) return '{{运行时注入}}';
  const head = value.slice(0, 8);
  return `${head}${'*'.repeat(Math.max(4, Math.min(12, value.length - 8)))}`;
}