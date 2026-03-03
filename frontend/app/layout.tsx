import "./globals.css";
import type { ReactNode } from "react";
import { Nav } from "../components/Nav";

export const metadata = {
  title: "Fin-Eye",
  description: "Understand the forces behind price movements",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-50 antialiased">
        <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6">
          <header className="mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">Fin-Eye</h1>
              <p className="text-sm text-slate-400">
                Educational market intelligence · not investment advice
              </p>
            </div>
            <Nav />
          </header>
          <main className="flex-1">{children}</main>
          <footer className="mt-8 border-t border-slate-800 pt-4 text-xs text-slate-500">
            <p>
              This application is for educational purposes only and does not
              constitute investment advice.
            </p>
          </footer>
        </div>
      </body>
    </html>
  );
}

