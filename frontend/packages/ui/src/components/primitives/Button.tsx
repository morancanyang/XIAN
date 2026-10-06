import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/cn';

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-control text-sm font-medium ' +
    'transition-colors duration-fast ease-out focus-visible:outline-none focus-visible:ring-2 ' +
    'focus-visible:ring-blue-team disabled:pointer-events-none disabled:opacity-50 ' +
    'aria-disabled:pointer-events-none aria-disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-blue-team text-white hover:bg-blue-team/90',
        danger: 'bg-red-team text-white hover:bg-red-team/90',
        outline: 'border border-border bg-transparent hover:bg-white/5',
        ghost: 'hover:bg-white/5',
        subtle: 'bg-white/10 text-content hover:bg-white/15'
      },
      size: {
        sm: 'h-8 px-3 text-xs',
        md: 'h-10 px-4',
        lg: 'h-11 px-6 text-base',
        icon: 'h-9 w-9'
      },
      loading: {
        true: 'cursor-wait opacity-70'
      }
    },
    defaultVariants: { variant: 'primary', size: 'md' }
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

/** 受控/非受控双形态 + asChild 组合（8.5 组件 API 约定）。 */
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, loading = false, asChild = false, children, disabled, ...props },
  ref
) {
  const Comp = asChild ? Slot : 'button';
  const classes = cn(buttonVariants({ variant, size, loading }), className);
  const attrs = {
    ref,
    className: classes,
    disabled: asChild ? undefined : disabled || loading,
    'aria-busy': loading || undefined,
    ...props
  };
  /* Slot 只接受单一元素子节点；asChild 时不得混入 Spinner 等额外子节点 */
  if (asChild) {
    return <Comp {...attrs}>{children}</Comp>;
  }
  return (
    <Comp {...attrs}>
      {loading ? <Spinner /> : null}
      {children}
    </Comp>
  );
});

function Spinner() {
  return (
    <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" aria-hidden="true">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}

export { buttonVariants };