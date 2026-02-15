import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'OpenClaw Command-Centre',
  description: 'Autonomous SMC/ICT Trading Agent',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}


