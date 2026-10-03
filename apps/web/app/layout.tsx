import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Quant Cockpit v1 | Trading OS",
  description: "Institutional Quant Operating System & Command Terminal",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark h-full">
      <body className="h-full bg-[#0a0b0d] text-[#f0f3f8] antialiased overflow-hidden selection:bg-cyan-500/30 selection:text-cyan-200">
        {children}
      </body>
    </html>
  );
}
