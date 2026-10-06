import * as React from 'react';
import * as CheckboxPrimitive from '@radix-ui/react-checkbox';
import * as SwitchPrimitive from '@radix-ui/react-switch';
import { cn } from '../../lib/cn';

export const Checkbox = React.forwardRef<
  React.ElementRef<typeof CheckboxPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>
>(function Checkbox({ className, ...props }, ref) {
  return (
    <CheckboxPrimitive.Root
      ref={ref}
      className={cn(
        'peer h-4 w-4 shrink-0 rounded-[4px] border border-border-strong bg-base',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-team',
        'data-[state=checked]:border-blue-team data-[state=checked]:bg-blue-team',
        className
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center text-white">
        <svg viewBox="0 0 24 24" className="h-3 w-3" aria-hidden="true">
          <path d="M20 6L9 17l-5-5" fill="none" stroke="currentColor" strokeWidth="3" />
        </svg>
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
});

export const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitive.Root>
>(function Switch({ className, ...props }, ref) {
  return (
    <SwitchPrimitive.Root
      ref={ref}
      className={cn(
        'peer inline-flex h-5 w-9 shrink-0 items-center rounded-pill border border-transparent',
        'transition-colors duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-team',
        'data-[state=checked]:bg-blue-team data-[state=unchecked]:bg-white/15',
        className
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        className={cn(
          'pointer-events-none block h-4 w-4 rounded-full bg-white shadow transition-transform duration-fast ease-out',
          'data-[state=checked]:translate-x-4 data-[state=unchecked]:translate-x-0.5'
        )}
      />
    </SwitchPrimitive.Root>
  );
});

export interface FieldProps {
  label: React.ReactNode;
  hint?: React.ReactNode;
  error?: string | null;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
  id?: string;
}

/** 表单项外壳：label + hint/error + 控件，统一错误展示（PRD 2.3.1）。 */
export function Field({ label, hint, error, required, children, className, id }: FieldProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      <label htmlFor={id} className="block text-sm font-medium text-content-muted">
        {label}
        {required ? <span className="ml-1 text-red-team">*</span> : null}
      </label>
      {children}
      {error ? (
        <p className="text-xs text-danger" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-content-faint">{hint}</p>
      ) : null}
    </div>
  );
}