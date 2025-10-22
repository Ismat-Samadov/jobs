import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Lead Generator",
    template: "%s | Lead Generator"
  },
  description: "Real estate lead generation and management system for EVV.AZ and Villa.AZ",
  keywords: ["lead generator", "real estate", "CRM", "leads management"],
  authors: [{ name: "Lead Generator Team" }],
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#2563eb',
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
