import type { Metadata } from "next";
import { Jost } from "next/font/google";
import "./globals.css";
import { BrandProvider } from "@/lib/brand-context";
import Header from "@/components/Header";

const jost = Jost({
  variable: "--font-jost",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "Ora Sleep — Creative Board",
  description: "Creative asset management for Ora Sleep",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="de"
      className={`${jost.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <BrandProvider>
          <Header />
          {children}
        </BrandProvider>
      </body>
    </html>
  );
}
