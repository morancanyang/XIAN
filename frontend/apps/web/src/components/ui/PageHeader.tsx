import type { ReactNode } from 'react';
import { cn } from '../../lib/utils/cn';

export interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div className={cn('mb-4 flex flex-wrap items-end justify-between gap-3', className)}>
      <div>
        <h1 className="text-lg font-semibold text-content">{title}</h1>
        {description ? <p className="mt-1 text-xs text-content-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}