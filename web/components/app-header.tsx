import { LogOut } from 'lucide-react'
import { Wordmark } from './brand'

export function AppHeader({
  section,
  role,
  onSignOut,
  children,
}: {
  section: string
  role?: 'ADMIN' | 'USER' | 'admin' | 'user'
  onSignOut?: () => void
  children?: React.ReactNode
}) {
  const isAdmin = role?.toUpperCase() === 'ADMIN'
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-black/85 backdrop-blur-md">
      <div className="mx-auto flex h-[68px] max-w-[1400px] items-center justify-between gap-6 px-5 md:px-8">
        <div className="flex min-w-0 items-center gap-5">
          <Wordmark className="!text-[1.45rem]" />
          <span aria-hidden="true" className="hidden h-5 w-px bg-line sm:block" />
          <span className="hidden truncate text-[0.95rem] text-fg-2 sm:block">{section}</span>
        </div>
        <div className="flex items-center gap-4">
          {children}
          {role && (
            <span className="rounded-full border border-line px-3 py-1 text-[0.8rem] text-fg-2">
              {isAdmin ? 'Admin' : 'Reviewer'}
            </span>
          )}
          {onSignOut && (
            <button type="button" onClick={onSignOut} className="btn-quiet sm">
              <LogOut className="h-4 w-4" strokeWidth={1.5} aria-hidden="true" />
              <span>Sign out</span>
            </button>
          )}
        </div>
      </div>
    </header>
  )
}

export function PageIntro({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="mb-10 md:mb-14">
      <h1 className="font-display text-[clamp(2.1rem,3.4vw,3rem)] leading-[1.08] tracking-[-0.015em]">
        <span className="metal">{title}</span>
      </h1>
      {children && <p className="mt-3 max-w-[62ch] text-[1.05rem] leading-relaxed text-fg-2">{children}</p>}
    </div>
  )
}
