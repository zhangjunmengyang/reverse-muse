'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { BookOpen, ArrowRight, Ghost } from 'lucide-react';

export default function Home() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Hero Section */}
      <main className="flex-1 flex items-center justify-center px-6">
        <div className="max-w-2xl mx-auto text-center">
          {/* Logo */}
          <div
            className={`
              inline-flex items-center justify-center w-20 h-20 rounded-2xl
              bg-[var(--ghost-bg)] border border-[var(--ghost-border)]
              mb-8 animate-ghost-float
              ${mounted ? 'opacity-100' : 'opacity-0'}
              transition-opacity duration-700
            `}
          >
            <Ghost className="w-10 h-10 text-[var(--accent-secondary)]" />
          </div>

          {/* Title */}
          <h1
            className={`
              font-display text-5xl md:text-6xl font-semibold tracking-tight mb-4
              ${mounted ? 'animate-slide-up' : 'opacity-0'}
            `}
          >
            <span className="text-gradient">Reverse Muse</span>
          </h1>

          {/* Subtitle */}
          <p
            className={`
              text-xl text-[var(--text-secondary)] mb-12 max-w-lg mx-auto
              ${mounted ? 'animate-slide-up stagger-1' : 'opacity-0'}
            `}
          >
            AI-powered paper reading companion with contextual insights
          </p>

          {/* Action Button */}
          <div
            className={`
              flex justify-center
              ${mounted ? 'animate-slide-up stagger-2' : 'opacity-0'}
            `}
          >
            <Link
              href="/reading"
              className="btn btn-primary text-lg px-8 py-4 group"
            >
              <BookOpen className="w-5 h-5" />
              <span>Enter</span>
              <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 text-center text-[var(--text-muted)] text-sm">
        <p>Select text while reading to get AI-generated insights</p>
      </footer>
    </div>
  );
}
