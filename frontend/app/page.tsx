'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import Link from 'next/link';
import { FileText, Users, Vote, MessageSquare, ArrowRight, Gavel, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { GlassCard } from '@/components/glass-card';

export default function Home() {
  const { data: billsData } = useQuery({
    queryKey: ['bills', { parliament: 44, session: 1, limit: 5, offset: 0 }],
    queryFn: () =>
      apiClient.getBills({
        parliament: 44,
        session: 1,
        limit: 5,
        offset: 0,
        sort: 'introduced_date',
        order: 'desc',
      }),
  });

  const {
    data: overviewStats,
    isLoading: overviewLoading,
    isError: overviewError,
  } = useQuery({
    queryKey: ['overview-stats'],
    queryFn: () => apiClient.getOverviewStats(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: committeesData, isLoading: committeesLoading, isError: committeesError } = useQuery({
    queryKey: ['committees', { limit: 6 }],
    queryFn: () => apiClient.getCommittees({ limit: 6 }),
  });

  const stats = [
    {
      icon: FileText,
      label: 'Bills',
      value: overviewStats?.bills ?? billsData?.total ?? 0,
      color: 'from-blue-500 to-cyan-500',
      href: '/bills',
      loading: overviewLoading && !overviewStats && !billsData,
    },
    {
      icon: Gavel,
      label: 'Committees',
      value: overviewStats?.committees ?? committeesData?.total ?? 0,
      color: 'from-indigo-500 to-purple-500',
      href: '/committees',
      loading: overviewLoading && !overviewStats && !committeesData,
    },
    {
      icon: Users,
      label: 'Politicians',
      value: overviewStats?.politicians ?? 0,
      color: 'from-purple-500 to-pink-500',
      href: '/politicians',
      loading: overviewLoading && !overviewStats,
    },
    {
      icon: Vote,
      label: 'Votes',
      value: overviewStats?.votes ?? 0,
      color: 'from-emerald-500 to-teal-500',
      href: '/votes',
      loading: overviewLoading && !overviewStats,
    },
    {
      icon: MessageSquare,
      label: 'Debates',
      value: overviewStats?.debates ?? 0,
      color: 'from-orange-500 to-red-500',
      href: '/debates',
      loading: overviewLoading && !overviewStats,
    },
  ];

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-accent-conservative/20 via-accent-ndp/20 to-accent-liberal/20" />
        
        <div className="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-5xl font-bold text-text-primary md:text-6xl">
              TrueCivic
            </h1>
            <p className="mt-4 text-xl text-text-secondary md:text-2xl">
              Explore Canadian Federal Parliament
            </p>
            <p className="mt-4 max-w-2xl mx-auto text-lg text-text-tertiary">
              Beautiful, fluid visualizations of bills, politicians, votes, and debates with liquid glass design.
            </p>
          </motion.div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat, index) => (
            <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: index * 0.1 }}>
              <Link href={stat.href}>
                <GlassCard variant="hover">
                  <div className="flex items-center justify-between mb-4">
                    <stat.icon className="h-8 w-8 text-accent-conservative" />
                    <ArrowRight className="h-5 w-5 text-text-tertiary transition-all" />
                  </div>
                  <div className="space-y-1">
                    <div className="text-3xl font-bold text-text-primary">
                      {stat.loading ? (
                        <Loader2 className="h-6 w-6 animate-spin text-text-tertiary" aria-hidden="true" />
                      ) : (
                        stat.value.toLocaleString()
                      )}
                    </div>
                    <p className="text-sm text-text-tertiary">{stat.label}</p>
                  </div>
                </GlassCard>
              </Link>
            </motion.div>
          ))}
        </div>
        {overviewError ? (
          <p className="mt-4 text-sm text-status-pending">
            Unable to fetch live overview statistics. Showing cached values where available.
          </p>
        ) : overviewStats?.generated_at ? (
          <p className="mt-4 text-sm text-text-tertiary">
            Stats updated{' '}
            {new Date(overviewStats.generated_at).toLocaleString('en-CA', {
              dateStyle: 'medium',
              timeStyle: 'short',
            })}
            .
          </p>
        ) : null}

        {/* Featured Committees */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-16"
        >
          <GlassCard>
            <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-semibold text-text-primary">Key Committees</h2>
                <p className="mt-1 text-sm text-text-tertiary">
                  Tracking the standing committees driving federal hearings.
                </p>
              </div>
              <Link
                href="/committees"
                className="inline-flex items-center gap-2 text-sm text-text-secondary transition-colors hover:text-accent-conservative"
              >
                View all
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            {committeesLoading ? (
              <div className="mt-6 flex items-center justify-center py-10 text-text-tertiary">
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Loading committees…
              </div>
            ) : committeesError ? (
              <div className="mt-6 py-10 text-center text-text-tertiary">
                Unable to load committees right now.
              </div>
            ) : committeesData?.committees?.length ? (
              <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {committeesData.committees.slice(0, 6).map((committee) => (
                  <div
                    key={committee.natural_id}
                    className="rounded-lg border border-glass/40 bg-surface-secondary/40 px-4 py-3 backdrop-blur transition-colors hover:border-glass"
                  >
                    <p className="text-xs uppercase tracking-widest text-accent-conservative">
                      {committee.committee_slug}
                    </p>
                    <h3 className="mt-1 text-sm font-semibold text-text-primary">
                      {committee.name_en || committee.acronym_en || committee.committee_slug}
                    </h3>
                    <p className="mt-2 text-xs text-text-tertiary">
                      Chamber: {committee.chamber}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-6 py-10 text-center text-text-tertiary">
                Committee data will appear here once ingestion runs.
              </div>
            )}
          </GlassCard>
        </motion.div>
      </div>

      {/* Footer */}
      <div className="border-t border-glass/40 py-12">
        <div className="mx-auto max-w-7xl px-4 text-center text-text-tertiary sm:px-6 lg:px-8">
          <p>Data sourced from OpenParliament API</p>
        </div>
      </div>
    </div>
  );
}
