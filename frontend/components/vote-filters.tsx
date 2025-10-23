'use client';

import { FilterBar, FilterDropdown } from '@/components/filter-bar';

interface VoteFiltersProps {
  result?: string;
  onResultChange?: (value: string) => void;
}

const RESULT_OPTIONS = [
  { value: 'all', label: 'All Results' },
  { value: 'passed', label: 'Passed' },
  { value: 'defeated', label: 'Defeated' },
];

export function VoteFilters({ result = 'all', onResultChange }: VoteFiltersProps) {
  return (
    <FilterBar>
      <FilterDropdown
        label="Result"
        value={result}
        onChange={onResultChange || (() => {})}
        options={RESULT_OPTIONS}
      />
    </FilterBar>
  );
}
