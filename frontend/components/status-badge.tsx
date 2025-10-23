import { ReactNode } from "react";
import { cn } from "@/lib/utils";

type StatusVariant =
  | "active"
  | "pending"
  | "completed"
  | "failed"
  | "first-reading"
  | "second-reading"
  | "third-reading"
  | "royal-assent";

interface StatusBadgeProps {
  status: StatusVariant;
  children?: ReactNode;
  size?: "sm" | "md" | "lg";
}

const statusConfig: Record<
  StatusVariant,
  {
    bg: string;
    text: string;
    dot: string;
  }
> = {
  active: {
    bg: "bg-status-active/10",
    text: "text-status-active",
    dot: "bg-status-active",
  },
  pending: {
    bg: "bg-status-pending/10",
    text: "text-status-pending",
    dot: "bg-status-pending",
  },
  completed: {
    bg: "bg-status-completed/10",
    text: "text-status-completed",
    dot: "bg-status-completed",
  },
  failed: {
    bg: "bg-status-failed/10",
    text: "text-status-failed",
    dot: "bg-status-failed",
  },
  "first-reading": {
    bg: "bg-accent-conservative/10",
    text: "text-accent-conservative",
    dot: "bg-accent-conservative",
  },
  "second-reading": {
    bg: "bg-accent-ndp/10",
    text: "text-accent-ndp",
    dot: "bg-accent-ndp",
  },
  "third-reading": {
    bg: "bg-accent-liberal/10",
    text: "text-accent-liberal",
    dot: "bg-accent-liberal",
  },
  "royal-assent": {
    bg: "bg-status-active/10",
    text: "text-status-active",
    dot: "bg-status-active",
  },
};

export function StatusBadge({
  status,
  children,
  size = "md",
}: StatusBadgeProps) {
  const config = statusConfig[status];
  const sizeClass = {
    sm: "px-2 py-1 text-xs",
    md: "px-3 py-1.5 text-sm",
    lg: "px-4 py-2 text-base",
  }[size];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border font-semibold uppercase tracking-wide",
        config.bg,
        config.text,
        sizeClass,
        `border-current/20`
      )}
      data-status={status}
    >
      <span
        className={cn("h-1.5 w-1.5 rounded-full", config.dot)}
        style={{
          animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        }}
      />
      {children || status}
    </span>
  );
}
