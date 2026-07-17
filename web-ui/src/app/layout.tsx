import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "../styles/globals.css";
import { QueryProvider } from "@/components/common/query-provider";
import { cn } from "@/lib/utils";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Research Discussion | MARS Baseline",
  description: "Scientific research discussion",
  other: { "study-condition": "baseline" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={cn("h-full", "antialiased", "font-sans", inter.variable)}
    >
      <body className="min-h-full flex flex-col">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
