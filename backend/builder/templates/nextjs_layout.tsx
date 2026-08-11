import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '{project_name}',
  description: '{description}',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}