"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export function ThemeToggle() {
  const [isDark, setIsDark] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const theme = document.documentElement.getAttribute("data-theme");
    setIsDark(theme === "dark");
  }, []);

  if (!mounted) {
    return (
      <button
        type="button"
        aria-label="Toggle theme"
        className="relative flex h-10 w-10 items-center justify-center rounded-full border border-glass bg-surface-primary text-text-secondary"
      >
        <Sun className="h-4 w-4" />
      </button>
    );
  }

  const handleToggle = () => {
    const root = document.documentElement;
    const newTheme = isDark ? "light" : "dark";
    root.setAttribute("data-theme", newTheme);
    setIsDark(!isDark);
    localStorage.setItem("theme", newTheme);
  };

  return (
    <button
      type="button"
      aria-label="Toggle theme"
      onClick={handleToggle}
      className="relative flex h-10 w-10 items-center justify-center rounded-full border border-glass bg-surface-primary text-text-secondary transition-colors hover:border-accent-conservative"
    >
      <motion.span
        key={isDark ? "dark" : "light"}
        initial={{ opacity: 0, scale: 0.6, rotate: -15 }}
        animate={{ opacity: 1, scale: 1, rotate: 0 }}
        exit={{ opacity: 0, scale: 0.6, rotate: 15 }}
        transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
        className="absolute inset-0 flex items-center justify-center"
      >
        {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </motion.span>
    </button>
  );
}
