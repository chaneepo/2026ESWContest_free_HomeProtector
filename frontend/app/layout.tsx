import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  metadataBase: new URL('https://care-pack-control.kimms13798.chatgpt.site'),
  title: 'CARE-PACK | 로봇 제어 시스템',
  description: '취약계층의 안전한 외출 준비를 돕는 CARE-PACK 스마트 로보틱스 제어 시스템',
  openGraph: {
    title: 'CARE-PACK | 로봇 제어 시스템',
    description: '안전한 외출 준비를 위한 로봇 제어 시스템',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: 'CARE-PACK 로봇 제어 시스템' }],
    locale: 'ko_KR',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CARE-PACK | 로봇 제어 시스템',
    description: '안전한 외출 준비를 위한 로봇 제어 시스템',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  );
}
