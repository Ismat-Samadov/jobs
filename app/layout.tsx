import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lead Generator - Admin Panel",
  description: "Manage your leads and users",
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
