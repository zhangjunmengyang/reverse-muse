import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Reverse Muse - AI Reading Companion',
  description: 'AI-powered reading companion with proactive insights',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-50 text-gray-900">
        {children}
      </body>
    </html>
  );
}
