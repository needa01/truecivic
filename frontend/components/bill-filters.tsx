'use client';

import { FilterBar, FilterDropdown } from '@/components/filter-bar';

interface BillFiltersProps {
  status?: string;
  onStatusChange?: (value: string) => void;
}

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'active', label: 'Active' },
  { value: 'first-reading', label: '1st Reading' },
  { value: 'second-reading', label: '2nd Reading' },
  { value: 'third-reading', label: '3rd Reading' },
  { value: 'royal-assent', label: 'Royal Assent' },
  { value: 'failed', label: 'Withdrawn/Died' },
];

export function BillFilters({ status = 'all', onStatusChange }: BillFiltersProps) {
  return (
    <FilterBar>
      <FilterDropdown
        label="Status"
        value={status}
        onChange={onStatusChange || (() => {})}
        options={STATUS_OPTIONS}
      />
    </FilterBar>
  );
}
