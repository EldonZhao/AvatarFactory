import * as React from 'react';
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]',
        secondary: 'bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))]',
        destructive: 'bg-[hsl(var(--destructive))] text-[hsl(var(--destructive-foreground))]',
        outline: 'border border-[hsl(var(--border))] text-[hsl(var(--foreground))]',
        success: 'bg-green-500/10 text-green-500 border border-green-500/20',
        warning: 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/20',
        info: 'bg-blue-500/10 text-blue-500 border border-blue-500/20',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
