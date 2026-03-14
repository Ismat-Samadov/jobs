import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });

export const metadata: Metadata = {
  title: 'Pudding Monsters – Sliding Puzzle Game',
  description: 'Slide jelly monsters to merge and cover all the stars! A fun, cute sliding puzzle game.',
  icons: {
    icon: '/favicon.svg',
  },
  openGraph: {
    title: 'Pudding Monsters',
    description: 'Slide jelly monsters to merge and cover all the stars!',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className={`${inter.className} antialiased overflow-x-hidden`}>{children}</body>
    </html>
  );
}
