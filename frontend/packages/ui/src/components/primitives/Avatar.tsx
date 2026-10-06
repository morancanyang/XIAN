import * as React from 'react';
import * as AvatarPrimitive from '@radix-ui/react-avatar';
import { cn } from '../../lib/cn';

export function Avatar({ className, ...props }: React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>) {
  return <AvatarPrimitive.Root className={cn('relative flex h-8 w-8 shrink-0 overflow-hidden rounded-full', className)} {...props} />;
}

export function AvatarImage(props: React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>) {
  return <AvatarPrimitive.Image className="aspect-square h-full w-full object-cover" {...props} />;
}

export function AvatarFallback({
  className,
  ...props
}: React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>) {
  return (
    <AvatarPrimitive.Fallback
      className={cn('flex h-full w-full items-center justify-center bg-white/10 text-xs font-medium', className)}
      {...props}
    />
  );
}