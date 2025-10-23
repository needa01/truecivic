import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  variant?: "default" | "hover" | "elevated";
  onClick?: () => void;
}

export function GlassCard({
  children,
  className,
  variant = "default",
  onClick,
}: GlassCardProps) {
  return (
    <div
      className={cn(
        "relative rounded-xl border border-glass bg-surface-primary backdrop-filter backdrop-blur p-6",
        "transition-all duration-300",
        variant === "hover" && "hover:border-accent-conservative hover:shadow-lg hover:-translate-y-1",
        variant === "elevated" && "shadow-lg",
        onClick && "cursor-pointer",
        className
      )}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </div>
  );
}
