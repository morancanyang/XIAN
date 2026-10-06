import * as React from 'react';
import { cn } from '../../lib/cn';

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={cn(
          'flex h-10 w-full rounded-control border border-border bg-base px-3 py-2 text-sm',
          'placeholder:text-content-faint transition-colors duration-fast',
          'focus-visible:border-blue-team focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-team',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      />
    );
  }
);

export const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, rows = 4, ...props }, ref) {
  return (
    <textarea
      ref={ref}
      rows={rows}
      className={cn(
        'flex w-full rounded-control border border-border bg-base px-3 py-2 font-mono text-sm',
        'placeholder:text-content-faint transition-colors duration-fast',
        'focus-visible:border-blue-team focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-team',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      {...props}
    />
  );
});