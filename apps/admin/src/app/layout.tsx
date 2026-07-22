import type { Metadata } from "next";
import { Fraunces, Manrope } from "next/font/google";
import "./globals.css";

const fraunces = Fraunces({
  variable: "--font-display-family",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const manrope = Manrope({
  variable: "--font-body-family",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MehndiVerse Admin",
  description: "Staff dashboard for managing MehndiVerse users, artists, and content.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${fraunces.variable} ${manrope.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-background text-text-primary font-body">
        {children}
      </body>
    </html>
  );
}
