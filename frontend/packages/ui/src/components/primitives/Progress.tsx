import * as React from 'react';
import * as ProgressPrimitive from '@radix-ui/react-progress';
import { cn } from '../../lib/cn';

export interface ProgressProps extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  tone?: 'blue' | 'red' | 'coach' | 'success';
  /** 柔光填充：低透明度渐变 + 弥散光晕，用于深空氛围页面（默认关闭，保持实色） */
  soft?: boolean;
}

const fillClass: Record<NonNullable<ProgressProps['tone']>, string> = {
  blue: 'bg-blue-team',
  red: 'bg-red-team',
  coach: 'bg-coach',
  success: 'bg-success'
};

/* soft 模式：横贯渐隐光带 + 柔和边缘，替代生硬实色块 */
const softFillClass: Record<NonNullable<ProgressProps['tone']>, string> = {
  blue: 'bg-gradient-to-r from-transparent via-blue-team to-transparent',
  red: 'bg-gradient-to-r from-transparent via-red-team to-transparent',
  coach: 'bg-gradient-to-r from-transparent via-coach to-transparent',
  success: 'bg-gradient-to-r from-transparent via-success to-transparent'
};

export const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressProps
>(function Progress({ className, value, tone = 'blue', soft = false, ...props }, ref) {
  const pct = Math.min(100, Math.max(0, value ?? 0));
  return (
    <ProgressPrimitive.Root
      ref={ref}
      value={pct}
      className={cn('relative h-2 w-full overflow-hidden rounded-pill bg-white/10', className)}
      {...props}
    >
      <ProgressPrimitive.Indicator
        className={cn(
          'h-full w-full flex-1 transition-transform duration-slow ease-out',
          soft ? cn(softFillClass[tone], 'opacity-70 blur-[1px]') : fillClass[tone]
        )}
        style={{ transform: `translateX(-${100 - pct}%)` }}
      />
    </ProgressPrimitive.Root>
  );
});