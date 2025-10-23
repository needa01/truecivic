'use client';

import { Menu, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// MARK: Mobile Navigation Menu ====================================================

const NAV_ITEMS = [
  { href: '/bills', label: 'Bills' },
  { href: '/votes', label: 'Votes' },
  { href: '/debates', label: 'Debates' },
  { href: '/committees', label: 'Committees' },
  { href: '/politicians', label: 'Politicians' },
];

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  const isActive = (href: string) => pathname === href;

  const handleLinkClick = () => {
    setIsOpen(false);
  };

  return (
    <>
      {/* Hamburger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle menu"
        aria-expanded={isOpen}
        className="relative h-10 w-10 flex items-center justify-center rounded-lg border border-glass bg-surface-primary text-text-secondary transition-colors hover:border-accent-conservative md:hidden"
      >
        {isOpen ? (
          <X className="h-5 w-5" />
        ) : (
          <Menu className="h-5 w-5" />
        )}
      </button>

      {/* Mobile Menu */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setIsOpen(false)}
              className="fixed inset-0 top-16 bg-black/20 backdrop-blur-sm z-40 md:hidden"
            />

            {/* Menu Content */}
            <motion.div
              initial={{ x: '-100%', opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: '-100%', opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className="fixed left-0 top-16 bottom-0 w-64 bg-surface-primary backdrop-filter backdrop-blur border-r border-glass z-50 md:hidden overflow-y-auto"
            >
              <nav className="flex flex-col gap-1 p-4">
                {NAV_ITEMS.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={handleLinkClick}
                    className={`relative px-4 py-3 rounded-lg font-medium transition-all duration-200 ${
                      isActive(item.href)
                        ? 'text-accent-conservative bg-surface-secondary'
                        : 'text-text-secondary hover:text-text-primary hover:bg-surface-secondary'
                    }`}
                  >
                    {item.label}
                    {isActive(item.href) && (
                      <motion.div
                        layoutId="mobile-active-indicator"
                        className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-accent-liberal to-accent-conservative rounded-r-full"
                        transition={{ type: 'spring', stiffness: 380, damping: 40 }}
                      />
                    )}
                  </Link>
                ))}
              </nav>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
