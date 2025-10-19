'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import Link from 'next/link';
import { FileText, Users, Vote, MessageSquare, ArrowRight, Gavel, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

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

  const { data: committeesData, isLoading: committeesLoading, isError: committeesError } = useQuery({
    queryKey: ['committees', { limit: 6 }],
    queryFn: () => apiClient.getCommittees({ limit: 6 }),
  });

  const stats = [
    {
      icon: FileText,
      label: 'Bills',
      value: billsData?.total || 0,
      color: 'from-blue-500 to-cyan-500',
      href: '/bills',
    },
    {
      icon: Gavel,
      label: 'Committees',
      value: committeesData?.total || 0,
      color: 'from-indigo-500 to-purple-500',
      href: '/committees',
    },
    {
      icon: Users,
      label: 'Politicians',
      value: 338,
      color: 'from-purple-500 to-pink-500',
      href: '/politicians',
    },
    {
      icon: Vote,
      label: 'Votes',
      value: 0,
      color: 'from-emerald-500 to-teal-500',
      href: '/votes',
    },
    {
      icon: MessageSquare,
      label: 'Debates',
      value: 0,
      color: 'from-orange-500 to-red-500',
      href: '/debates',
    },
  ];

  return (
    <div className="min-h-screen">
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-purple-600/20 to-pink-600/20" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center"
          >
            <h1 className="text-6xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent mb-6">
              TrueCivic
            </h1>
            <p className="text-2xl text-slate-300 mb-8">
              Explore Canadian Federal Parliament
            </p>
            <p className="text-lg text-slate-400 max-w-2xl mx-auto">
              Beautiful, fluid visualizations of bills, politicians, votes, and debates.
            </p>
          </motion.div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => (
            <motion.div key={stat.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: index * 0.1 }}>
              <Link href={stat.href}>
                <div className="group relative overflow-hidden rounded-2xl bg-slate-900/50 backdrop-blur border border-slate-800 hover:border-slate-700 transition-all duration-300 hover:scale-105">
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <stat.icon className="w-8 h-8" />
                      <ArrowRight className="w-5 h-5 text-slate-600 group-hover:text-slate-400 transition-all duration-300" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-3xl font-bold text-slate-100">{stat.value.toLocaleString()}</p>
                      <p className="text-sm text-slate-400">{stat.label}</p>
                    </div>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="mt-16 rounded-3xl border border-slate-800 bg-slate-900/40 backdrop-blur"
        >
          <div className="p-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-semibold text-slate-100">Key Committees</h2>
                <p className="text-sm text-slate-400">
                  Tracking the standing committees driving federal hearings.
                </p>
              </div>
              <Link
                href="/committees"
                className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-slate-100 transition-colors"
              >
                View all
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            {committeesLoading ? (
              <div className="flex items-center justify-center py-10 text-slate-400">
                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                Loading committees…
              </div>
            ) : committeesError ? (
              <div className="py-10 text-center text-slate-400">
                Unable to load committees right now.
              </div>
            ) : committeesData?.committees?.length ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {committeesData.committees.slice(0, 6).map((committee) => (
                  <div
                    key={committee.natural_id}
                    className="rounded-2xl border border-slate-800 bg-slate-900/50 px-5 py-4 hover:border-slate-700 transition-colors"
                  >
                    <p className="text-xs uppercase tracking-wide text-indigo-300">
                      {committee.committee_slug}
                    </p>
                    <h3 className="mt-1 text-sm font-semibold text-slate-100">
                      {committee.name_en || committee.acronym_en || committee.committee_slug}
                    </h3>
                    <p className="mt-2 text-xs text-slate-400">
                      Chamber: {committee.chamber}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-10 text-center text-slate-400">
                Committee data will appear here once ingestion runs.
              </div>
            )}
          </div>
        </motion.div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 border-t border-slate-800">
        <div className="text-center text-slate-400">
          <p>Data sourced from OpenParliament API</p>
        </div>
      </div>
    </div>
  );
}
