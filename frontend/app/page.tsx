'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import Link from 'next/link';
import { FileText, Users, Vote, MessageSquare, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Home() {
  const { data: billsData, isLoading: billsLoading } = useQuery({
    queryKey: ['bills', { parliament: 44, session: 1, page: 1, size: 5 }],
    queryFn: () => apiClient.getBills({ parliament: 44, session: 1, page: 1, size: 5 }),
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
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 border-t border-slate-800">
        <div className="text-center text-slate-400">
          <p>Data sourced from OpenParliament API</p>
        </div>
      </div>
    </div>
  );
}
