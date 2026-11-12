import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ClipViral - AI Viral Moment Clipper for YouTube & Socials",
  description: "Turn long videos into short viral vertical clips with AI scoring and direct YouTube Shorts publishing.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-purple-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
