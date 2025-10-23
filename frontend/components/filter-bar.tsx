import { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface FilterBarProps {
  children: ReactNode;
  className?: string;
}

export function FilterBar({ children, className }: FilterBarProps) {
  return (
    <div
      className={cn(
        "sticky top-16 z-40 flex gap-4 border-b border-glass bg-surface-secondary px-4 py-4 backdrop-filter backdrop-blur sm:px-6 lg:px-8",
        "animate-slide-down",
        className
      )}
      style={{
        animationDelay: "0.2s",
      }}
    >
      {children}
    </div>
  );
}

interface FilterDropdownProps {
  label: string;
  value?: string;
  options: Array<{ value: string; label: string }>;
  onChange?: (value: string) => void;
}

export function FilterDropdown({
  label,
  value,
  options,
  onChange,
}: FilterDropdownProps) {
  return (
    <select
      value={value || ""}
      onChange={(e) => onChange?.(e.target.value)}
      className={cn(
        "min-w-[140px] rounded-md border border-glass bg-surface-primary px-3 py-2",
        "text-sm font-medium text-text-primary",
        "transition-all hover:border-accent-conservative",
        "focus:outline-none focus:ring-2 focus:ring-accent-conservative/50"
      )}
      aria-label={label}
    >
      <option value="">{label}</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
