import type { Metadata } from 'next'
import '@fontsource/libre-caslon-display/400.css'
import '@fontsource-variable/inter'
import './globals.css'
import { AuthProvider } from '../lib/auth-context'

const description =
  'ClausePilot redlines inbound NDAs against your firm’s rules and returns a Word file with real tracked changes.'

export const metadata: Metadata = {
  title: 'ClausePilot — NDA redlining against your own rules',
  description,
  openGraph: {
    title: 'ClausePilot — NDA redlining against your own rules',
    description,
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
