import * as React from 'react';
import { cn } from '../../lib/cn';

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('animate-pulse rounded-control bg-white/5', className)} {...props} />;
}

export function Separator({
  className,
  orientation = 'horizontal',
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { orientation?: 'horizontal' | 'vertical' }) {
  return (
    <div
      role="separator"
      aria-orientation={orientation}
      className={cn(
        'shrink-0 bg-border',
        orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
        className
      )}
      {...props}
    />
  );
}

export function Kbd({ className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <kbd
      className={cn(
        'rounded border border-border bg-elevated px-1.5 py-0.5 font-mono text-[10px] text-content-muted',
        className
      )}
      {...props}
    />
  );
}

export function CodeBlock({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLPreElement>) {
  return (
    <pre
      className={cn(
        'overflow-x-auto rounded-control border border-border bg-sunken p-3 font-mono text-xs leading-relaxed text-content',
        className
      )}
      {...props}
    >
      <code>{children}</code>
    </pre>
  );
}