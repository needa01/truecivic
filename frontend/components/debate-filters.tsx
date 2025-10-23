'use client';

import { FilterBar, FilterDropdown } from '@/components/filter-bar';

interface DebateFiltersProps {
  chamber?: string;
  onChamberChange?: (value: string) => void;
}

const CHAMBER_OPTIONS = [
  { value: 'all', label: 'All Chambers' },
  { value: 'house of commons', label: 'House of Commons' },
  { value: 'senate', label: 'Senate' },
];

export function DebateFilters({ chamber = 'all', onChamberChange }: DebateFiltersProps) {
  return (
    <FilterBar>
      <FilterDropdown
        label="Chamber"
        value={chamber}
        onChange={onChamberChange || (() => {})}
        options={CHAMBER_OPTIONS}
      />
    </FilterBar>
  );
}
