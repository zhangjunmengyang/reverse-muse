import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Reverse Muse',
  description: 'Your AI reading companion with ghostly insights',
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN" className="dark">
      <head>
        <meta name="theme-color" content="#0a0b0f" />
      </head>
      <body className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] antialiased">
        {/* Background ambient glow */}
        <div className="fixed inset-0 bg-radial-glow pointer-events-none" />
        <div className="fixed inset-0 bg-grid pointer-events-none opacity-50" />

        {/* Main content */}
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}
