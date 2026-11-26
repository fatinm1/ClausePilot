import Link from 'next/link'
import { PaperSheets, Wordmark } from './brand'

export function AuthShell({
  title,
  intro,
  children,
  footer,
}: {
  title: React.ReactNode
  intro: string
  children: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <div className="grid min-h-screen bg-black text-white lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <div className="flex flex-col px-[var(--pad-x)] py-8 lg:px-16 xl:px-24">
        <header className="flex items-center justify-between">
          <Wordmark />
          <Link href="/" className="text-[0.95rem] text-fg-2 hover:text-white">
            Back to site
          </Link>
        </header>
        <main className="flex flex-1 items-center py-16">
          <div className="w-full max-w-[440px]">
            <h1 className="font-display text-[clamp(2.25rem,3.6vw,3.25rem)] leading-[1.08] tracking-[-0.015em]">{title}</h1>
            <p className="mt-4 text-[1.05rem] leading-relaxed text-fg-2">{intro}</p>
            <div className="mt-10">{children}</div>
            <div className="mt-8 text-[0.95rem] text-fg-2">{footer}</div>
          </div>
        </main>
      </div>

      <aside
        aria-hidden="true"
        className="relative isolate hidden overflow-hidden border-l border-line bg-ink-raised lg:sticky lg:top-0 lg:flex lg:h-screen lg:items-center lg:justify-center"
      >
        <div
          className="absolute inset-0 -z-10"
          style={{ background: 'radial-gradient(55% 50% at 50% 45%, rgba(203,206,210,0.09), rgba(0,0,0,0) 70%)' }}
        />
        <div className="w-[min(460px,70%)] [perspective:1600px]">
          <div className="sheet-drift">
            <PaperSheets id="auth" className="sheet-tilt w-full" />
          </div>
        </div>
        <p className="absolute bottom-12 left-12 right-12 font-display text-[1.6rem] leading-snug">
          <span className="text-fg-3">The obligations shall survive for </span>
          <span className="tc-del">five (5)</span> <span className="tc-ins">two (2)</span>
          <span className="text-fg-3"> years.</span>
        </p>
      </aside>
    </div>
  )
}

export function FieldError({ id, children }: { id: string; children?: React.ReactNode }) {
  if (!children) return null
  return (
    <p id={id} className="mt-2 text-sm text-redline-text">
      {children}
    </p>
  )
}

export function FormAlert({ children }: { children?: React.ReactNode }) {
  if (!children) return null
  return (
    <div role="alert" className="mb-6 rounded-xl border border-redline/50 bg-redline-wash px-4 py-3 text-[0.95rem] text-redline-text">
      {children}
    </div>
  )
}

export function FullPageLoading({ label = 'Loading' }: { label?: string }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-black text-fg-2" role="status">
      <div className="flex items-center gap-3">
        <span className="spinner" />
        <span>{label}</span>
      </div>
    </div>
  )
}
