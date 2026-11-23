import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Customer Support Assistant',
  description: 'A workspace for reviewing AI-assisted customer support responses.',
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body className="bg-slate-50 font-sans text-slate-950 antialiased">{children}</body>
    </html>
  );
}
