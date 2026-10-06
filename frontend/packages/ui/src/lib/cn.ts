import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** 组件样式合并：`cn()` 是 8.5 组件 API 约定的一部分，className 可覆盖默认样式。 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}