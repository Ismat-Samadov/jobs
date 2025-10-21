import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Lead Generator",
    template: "%s | Lead Generator"
  },
  description: "Real estate lead generation and management system for EVV.AZ and Villa.AZ",
  keywords: ["lead generator", "real estate", "CRM", "leads management"],
  authors: [{ name: "Lead Generator Team" }],
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
  manifest: '/manifest.json',
  themeColor: '#2563eb',
  viewport: {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
