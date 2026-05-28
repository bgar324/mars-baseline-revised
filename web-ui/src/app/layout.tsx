import type { Metadata } from "next";
import { Trykker, Fragment_Mono, Inter } from "next/font/google";
import "../styles/globals.css";
import { cn } from "@/lib/utils";

const inter = Inter({subsets:['latin'],variable:'--font-sans'});

const trykker = Trykker({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: "400",
});

const fragmentMono = Fragment_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: "400",
});

export const metadata: Metadata = {
  title: "prototype",
  description: "scientific hypothesis generation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={cn("h-full", "antialiased", trykker.variable, fragmentMono.variable, "font-sans", inter.variable)}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
