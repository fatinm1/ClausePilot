'use client'

import Link from 'next/link'
import { useEffect, useRef, useState } from 'react'
import { Menu, X } from 'lucide-react'
import { PaperSheets, SectionMark, Wordmark } from '../components/brand'

const SECTIONS = [
  { id: 'top', label: 'Introduction' },
  { id: 'sequence', label: 'How a review runs' },
  { id: 'rules', label: 'Your rules' },
  { id: 'process', label: 'Four steps' },
  { id: 'output', label: 'The Word file' },
  { id: 'start', label: 'Get started' },
]

const NAV = [
  { href: '#rules', label: 'Rules' },
  { href: '#process', label: 'How it works' },
  { href: '#output', label: 'Output' },
]

/* ---------- Header: wordmark starts centred, slides left on scroll ---------- */
function SiteHeader() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 48)
    on()
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [])

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-[background-color,border-color] duration-500 ${
        scrolled || open ? 'bg-black/80 backdrop-blur-md border-b border-line' : 'border-b border-transparent'
      }`}
    >
      <div className="wrap relative flex h-[76px] items-center justify-between">
        <div
          className="absolute top-1/2 transition-[left,transform] duration-[600ms] ease-out max-lg:!left-[var(--pad-x)] max-lg:!translate-x-0 max-lg:-translate-y-1/2"
          style={{
            left: scrolled ? 'var(--pad-x)' : '50%',
            transform: scrolled ? 'translate(0,-50%)' : 'translate(-50%,-50%)',
          }}
        >
          <Wordmark />
        </div>
        <span />
        <nav aria-label="Primary" className="hidden items-center gap-8 lg:flex">
          <div
            className={`flex items-center gap-8 transition-[opacity,transform] duration-500 ease-out ${
              scrolled ? 'opacity-100 translate-y-0' : 'pointer-events-none opacity-0 -translate-y-1'
            }`}
            aria-hidden={!scrolled}
          >
            {NAV.map((n) => (
              <a key={n.href} href={n.href} tabIndex={scrolled ? 0 : -1} className="text-[0.95rem] text-fg-2 transition-colors hover:text-white">
                {n.label}
              </a>
            ))}
          </div>
          <Link href="/login" className="text-[0.95rem] text-fg-2 transition-colors hover:text-white">
            Sign in
          </Link>
          <Link
            href="/demo"
            tabIndex={scrolled ? 0 : -1}
            aria-hidden={!scrolled}
            className={`btn-metal sm transition-[opacity,transform] duration-500 ${scrolled ? 'opacity-100' : 'pointer-events-none opacity-0 translate-y-[-4px]'}`}
          >
            Open the demo
          </Link>
        </nav>
        <button
          type="button"
          className="lg:hidden inline-flex h-10 w-10 items-center justify-center rounded-full border border-line text-white"
          aria-expanded={open}
          aria-controls="mobile-nav"
          aria-label={open ? 'Close menu' : 'Open menu'}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X className="h-4 w-4" strokeWidth={1.5} /> : <Menu className="h-4 w-4" strokeWidth={1.5} />}
        </button>
      </div>
      <div
        id="mobile-nav"
        className={`lg:hidden overflow-hidden transition-[max-height,opacity] duration-300 ${open ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}
      >
        <nav aria-label="Mobile" className="wrap flex flex-col gap-1 pb-6">
          {NAV.map((n) => (
            <a key={n.href} href={n.href} onClick={() => setOpen(false)} className="py-3 text-lg text-fg-2 border-b border-line">
              {n.label}
            </a>
          ))}
          <Link href="/login" className="py-3 text-lg text-fg-2 border-b border-line">Sign in</Link>
          <Link href="/demo" className="btn-metal mt-4 self-start">Open the demo</Link>
        </nav>
      </div>
    </header>
  )
}

/* ---------- Left section rail ---------- */
function ScreenRail({ active, progress }: { active: number; progress: number }) {
  return (
    <nav
      aria-label="Sections"
      className="fixed left-6 top-1/2 z-40 hidden -translate-y-1/2 flex-col items-center gap-3 xl:flex"
    >
      <SectionMark className="mb-2 text-2xl text-fg-3" />
      <div className="relative flex flex-col items-center gap-1">
        <span
          aria-hidden="true"
          className="absolute left-1/2 top-0 w-px -translate-x-1/2 bg-gradient-to-b from-white/0 via-white/60 to-white/0 transition-[top] duration-300"
          style={{ top: `calc(${progress * 100}% - 18px)`, height: 36 }}
        />
        {SECTIONS.map((s, i) => (
          <a
            key={s.id}
            href={`#${s.id}`}
            aria-label={`Go to ${s.label}`}
            aria-current={active === i ? 'true' : undefined}
            className={`grid h-8 w-8 place-items-center rounded-full text-[0.8rem] tabular-nums transition-[color,opacity] duration-300 ${
              active === i ? 'text-white opacity-100' : 'text-fg-2 opacity-40 hover:opacity-80'
            }`}
          >
            {i + 1}
          </a>
        ))}
      </div>
    </nav>
  )
}

/* ---------- Hero ---------- */
function Hero() {
  const ref = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect()
      el.style.setProperty('--metal-px', `${((e.clientX - r.left) / r.width) * 100}%`)
      el.style.setProperty('--metal-py', `${((e.clientY - r.top) / r.height) * 100}%`)
    }
    window.addEventListener('pointermove', move, { passive: true })
    return () => window.removeEventListener('pointermove', move)
  }, [])

  return (
    <section id="top" className="relative isolate flex min-h-[100svh] items-center overflow-hidden pt-[76px]">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            'radial-gradient(50% 45% at 70% 45%, rgba(203,206,210,0.10), rgba(0,0,0,0) 70%), radial-gradient(40% 40% at 20% 90%, rgba(176,69,69,0.07), rgba(0,0,0,0) 70%)',
        }}
      />
      <div aria-hidden="true" className="pointer-events-none absolute -right-[4%] top-[16%] -z-10 w-[min(520px,62vw)] opacity-60 [perspective:1600px] max-md:-right-[30%] max-md:opacity-35">
        <div className="sheet-drift">
          <PaperSheets id="hero" className="sheet-tilt w-full" />
        </div>
      </div>

      <div className="wrap">
        <h1
          ref={ref}
          className="font-display max-w-[15ch] text-[length:var(--fs-hero)] leading-[1.04] tracking-[-0.02em]"
        >
          <span className="metal">Mark up the NDA you </span>
          <span className="rl-del">were sent</span>{' '}
          <span className="rl-ins">
            <span className="metal">would have written.</span>
          </span>
        </h1>
        <p className="rise mt-8 max-w-[46ch] text-[length:var(--fs-body-lg)] leading-[1.5] text-fg-2" style={{ animationDelay: '1.1s' }}>
          Upload the counterparty’s draft. ClausePilot applies your firm’s standing positions and hands back a
          Word file with every edit as a tracked change.
        </p>
        <div className="rise mt-10 flex flex-wrap items-center gap-4" style={{ animationDelay: '1.25s' }}>
          <Link href="/demo" className="btn-metal">Open the demo</Link>
          <Link href="/register" className="btn-quiet">Create an account</Link>
        </div>
      </div>
    </section>
  )
}

/* ---------- Pinned scroll sequence ---------- */
const STATEMENTS = [
  'The counterparty sends their draft.',
  'Your rules decide what changes.',
  'ClausePilot writes the redline.',
]

function Sequence({ onProgress }: { onProgress?: (p: number) => void }) {
  const ref = useRef<HTMLElement>(null)
  const [p, setP] = useState(0)
  useEffect(() => {
    let raf = 0
    const on = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const el = ref.current
        if (!el) return
        const r = el.getBoundingClientRect()
        const total = r.height - window.innerHeight
        const v = Math.min(1, Math.max(0, -r.top / total))
        setP(v)
        onProgress?.(v)
      })
    }
    on()
    window.addEventListener('scroll', on, { passive: true })
    window.addEventListener('resize', on)
    return () => {
      window.removeEventListener('scroll', on)
      window.removeEventListener('resize', on)
      cancelAnimationFrame(raf)
    }
  }, [onProgress])

  const active = Math.min(2, Math.floor(p * 3.2))
  const finalScale = 1 + Math.max(0, Math.min(1, (p - 0.66) / 0.3)) * 0.28

  return (
    <section id="sequence" ref={ref} className="relative h-[300vh]" aria-label="How a review runs">
      <div className="sticky top-0 flex h-[100svh] items-center overflow-hidden">
        <div className="wrap">
          <ol className="space-y-6 md:space-y-8">
            {STATEMENTS.map((s, i) => {
              const isLast = i === STATEMENTS.length - 1
              return (
                <li
                  key={s}
                  className="font-display origin-left text-[length:var(--fs-scroll)] leading-[1.1] tracking-[-0.015em] transition-opacity duration-500"
                  style={{
                    opacity: i === active ? 1 : i < active ? 0.3 : 0.14,
                    transform: isLast ? `scale(${finalScale})` : undefined,
                  }}
                >
                  {isLast ? (
                    <>
                      <span className={i === active ? 'metal' : ''}>ClausePilot writes the </span>
                      <span className="relative inline-block">
                        <span className={i === active ? 'metal' : ''}>redline.</span>
                        <span
                          aria-hidden="true"
                          className="absolute left-0 right-[0.25em] top-[1.02em] h-[3px] origin-left rounded bg-redline transition-transform duration-700 ease-out"
                          style={{ transform: `scaleX(${i === active ? 1 : 0})` }}
                        />
                      </span>
                    </>
                  ) : (
                    <span className={i === active ? 'metal' : ''}>{s}</span>
                  )}
                </li>
              )
            })}
          </ol>
        </div>
      </div>
    </section>
  )
}

/* ---------- Rules specimen: the proof ---------- */
const RULES = [
  { id: 'term', title: 'Cap the confidentiality term', body: 'Any survival period longer than your limit is struck and replaced with it. Here: two years.' },
  { id: 'reps', title: 'Widen “Representatives”', body: 'Investors, agents, advisors and potential financing sources are added if the definition leaves them out.' },
  { id: 'retain', title: 'Keep an archival copy', body: 'A retention carve-out is inserted after the return-or-destroy clause.' },
  { id: 'sign', title: 'Complete the signature block', body: 'Your firm name, signer and title are filled from the firm details you saved.' },
]

function Specimen() {
  const [focus, setFocus] = useState<string | null>(null)
  const dim = (id: string) =>
    `transition-[opacity,background-color] duration-300 rounded-[3px] ${
      focus && focus !== id ? 'opacity-35' : 'opacity-100'
    } ${focus === id ? 'bg-white/[0.06]' : ''}`

  return (
    <section id="rules" className="relative py-24 md:py-32">
      <div className="wrap">
        <h2 className="font-display max-w-[22ch] text-[length:var(--fs-section)] leading-[1.12] tracking-[-0.015em]">
          <span className="metal">Write your positions once.</span>{' '}
          <span className="text-fg-3">Every NDA after that is read against them.</span>
        </h2>

        <div className="mt-16 grid gap-10 lg:mt-24 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-16">
          <div>
            <p className="mb-4 text-[0.95rem] text-fg-3">Point at a rule to see the edit it made.</p>
            <ul className="border-t border-line" aria-label="Rules applied to the sample">
              {RULES.map((r) => (
                <li key={r.id} className="border-b border-line">
                  <button
                    type="button"
                    onMouseEnter={() => setFocus(r.id)}
                    onMouseLeave={() => setFocus(null)}
                    onFocus={() => setFocus(r.id)}
                    onBlur={() => setFocus(null)}
                    aria-pressed={focus === r.id}
                    className="group grid w-full grid-cols-[1.25rem_1fr] gap-4 py-6 text-left"
                  >
                    <span
                      aria-hidden="true"
                      className={`mt-[0.55rem] h-[2px] w-full origin-left rounded bg-redline transition-transform duration-300 ease-out ${
                        focus === r.id ? 'scale-x-100' : 'scale-x-[0.35]'
                      }`}
                    />
                    <span>
                      <span className={`block text-[1.12rem] font-[480] transition-colors ${focus && focus !== r.id ? 'text-fg-2' : 'text-white'}`}>
                        {r.title}
                      </span>
                      <span className="mt-1.5 block text-[0.98rem] leading-relaxed text-fg-2">{r.body}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <figure className="relative">
            <div className="rounded-[22px] border border-line bg-ink-raised p-2 shadow-[0_40px_80px_-40px_rgba(0,0,0,0.9)]">
              <div className="rounded-[16px] bg-[#f4f4f2] px-7 py-8 text-[#1d1d1d] sm:px-12 sm:py-12">
                <p className="text-center font-display text-[1.35rem] tracking-[0.01em] text-[#111]">Mutual Non-Disclosure Agreement</p>
                <div className="mt-8 space-y-5 font-[Georgia,serif] text-[0.98rem] leading-[1.75]">
                  <p className={dim('reps')}>
                    <b>2. Representatives.</b> “Representatives” means a party’s affiliates, directors, officers and employees
                    <ins className="doc-ins">, and its investors, agents, advisors and potential financing sources</ins>.
                  </p>
                  <p className={dim('term')}>
                    <b>5. Term.</b> The obligations of the Recipient shall survive for a period of{' '}
                    <del className="doc-del">five (5)</del> <ins className="doc-ins">two (2)</ins> years from the date hereof.
                  </p>
                  <p className={dim('retain')}>
                    <b>7. Return of Materials.</b> Upon written request, the Recipient shall return or destroy all Confidential Information.
                    <ins className="doc-ins">
                      {' '}Notwithstanding the foregoing, Recipient may retain an electronic copy of Confidential Information if required under
                      Recipient’s document retention policy, provided that such retained materials remain subject to the confidentiality
                      obligations set forth herein.
                    </ins>
                  </p>
                  <div className={`grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 pt-2 ${dim('sign')}`}>
                    <span>By:</span>
                    <span><del className="doc-del">____________</del> <ins className="doc-ins">Jordan Ellis</ins></span>
                    <span>Title:</span>
                    <span><ins className="doc-ins">Managing Partner</ins></span>
                    <span>Firm:</span>
                    <span><ins className="doc-ins">Halden Capital LLC</ins></span>
                  </div>
                </div>
              </div>
            </div>
            <figcaption className="mt-4 text-sm text-fg-3">
              Sample clause text and names written for this page. Struck text is deleted, underlined text is inserted.
            </figcaption>
          </figure>
        </div>
      </div>
    </section>
  )
}

/* ---------- Four steps, as a stack of sheets ---------- */
const STEPS = [
  { t: 'Upload the counterparty’s .docx', d: 'Word documents only, so the formatting you send back is the formatting you received.' },
  { t: 'Choose the rules to apply', d: 'Your admin maintains the rule set. Pick the ones that fit this deal.' },
  { t: 'Accept or reject each change', d: 'Every proposed edit is listed with the rule that produced it. Nothing is applied without you.' },
  { t: 'Download the redline', d: 'A Word file with native tracked changes, ready to send back.' },
]

function Process() {
  return (
    <section id="process" className="relative overflow-hidden py-24 md:py-32">
      <div className="wrap grid items-center gap-16 lg:grid-cols-2">
        <div>
          <h2 className="font-display max-w-[18ch] text-[length:var(--fs-section)] leading-[1.12] tracking-[-0.015em]">
            <span className="text-fg-3">You stay the reviewer.</span>{' '}
            <span className="metal">ClausePilot does the typing.</span>
          </h2>
          <p className="mt-6 max-w-[44ch] text-[length:var(--fs-body-lg)] leading-[1.55] text-fg-2">
            A language model proposes edits inside the rules you selected. If no model is reachable, ClausePilot falls
            back to rule-based edits, so a review still runs.
          </p>
        </div>

        <ol className="relative mx-auto w-full max-w-[560px] [perspective:1400px]" aria-label="Four steps">
          {STEPS.map((s, i) => (
            <li
              key={s.t}
              className="relative mb-[-18px] rounded-[20px] border bg-black px-6 py-6 sm:px-7 md:translate-x-[var(--o)]"
              style={{
                borderColor: `rgba(255,255,255,${0.4 - i * 0.07})`,
                ['--o' as string]: `${i * 14}px`,
                zIndex: 10 - i,
                boxShadow: '0 24px 40px -24px rgba(0,0,0,.95)',
              }}
            >
              <div className="flex items-baseline gap-4">
                <span className="font-display text-2xl text-fg-3 tabular-nums">{i + 1}</span>
                <div>
                  <h3 className="text-[1.1rem] font-[480] text-white">{s.t}</h3>
                  <p className="mt-1 text-[0.97rem] leading-relaxed text-fg-2">{s.d}</p>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

/* ---------- Output: Word review pane ---------- */
const REVISIONS = [
  { kind: 'Deleted', text: 'five (5)', rule: 'Cap the confidentiality term' },
  { kind: 'Inserted', text: 'two (2)', rule: 'Cap the confidentiality term' },
  { kind: 'Inserted', text: ', and its investors, agents, advisors…', rule: 'Widen “Representatives”' },
  { kind: 'Inserted', text: 'Notwithstanding the foregoing, Recipient may…', rule: 'Keep an archival copy' },
  { kind: 'Inserted', text: 'Jordan Ellis', rule: 'Complete the signature block' },
]

function Output() {
  return (
    <section id="output" className="relative py-24 md:py-32">
      <div className="wrap">
        <h2 className="font-display max-w-[24ch] text-[length:var(--fs-section)] leading-[1.12] tracking-[-0.015em]">
          <span className="metal">It opens in Word as tracked changes,</span>{' '}
          <span className="text-fg-3">not as a list of suggestions you retype.</span>
        </h2>

        <div className="mt-16 grid gap-12 lg:mt-24 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
          <div className="overflow-hidden rounded-[22px] border border-line bg-ink-raised">
            <div className="flex items-center justify-between border-b border-line px-6 py-4">
              <span className="text-[0.95rem] text-white">Revisions</span>
              <span className="text-sm text-fg-3 tabular-nums">5 tracked changes</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[520px] text-left text-[0.95rem]">
                <thead>
                  <tr className="text-fg-3">
                    <th scope="col" className="px-6 py-3 font-normal">Change</th>
                    <th scope="col" className="px-6 py-3 font-normal">Text</th>
                    <th scope="col" className="px-6 py-3 font-normal">Rule</th>
                  </tr>
                </thead>
                <tbody>
                  {REVISIONS.map((r, i) => (
                    <tr key={i} className="border-t border-line">
                      <td className="px-6 py-4 text-fg-2">{r.kind}</td>
                      <td className="px-6 py-4">
                        <span className={r.kind === 'Deleted' ? 'tc-del' : 'tc-ins'}>{r.text}</span>
                      </td>
                      <td className="px-6 py-4 text-fg-2 whitespace-nowrap">{r.rule}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 className="text-[1.15rem] font-[480] text-white">What happens to your documents</h3>
            <dl className="mt-6 divide-y divide-line border-y border-line">
              {[
                ['Two roles', 'Admins write rules and manage users. Reviewers upload, review and download.'],
                ['In transit', 'Traffic between your browser and ClausePilot runs over HTTPS.'],
                ['Deleting', 'Deleting a document removes the upload and the redlined output from the server.'],
                ['The model', 'Clause text is sent to a hosted language model (Groq by default) to propose edits.'],
              ].map(([t, d]) => (
                <div key={t} className="grid gap-1 py-5 sm:grid-cols-[8rem_1fr] sm:gap-6">
                  <dt className="text-white">{t}</dt>
                  <dd className="text-fg-2 leading-relaxed">{d}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ---------- Close ---------- */
function Close() {
  return (
    <section id="start" className="py-24 md:py-32">
      <div className="wrap">
        <div className="relative isolate overflow-hidden rounded-[28px] border border-line bg-ink-raised px-8 py-16 sm:px-14 md:py-24">
          <div aria-hidden="true" className="pointer-events-none absolute -bottom-24 -right-10 -z-10 w-[420px] opacity-40 [perspective:1600px] max-md:w-[300px] max-md:opacity-25">
            <PaperSheets id="close" className="sheet-tilt w-full" />
          </div>
          <h2 className="font-display max-w-[20ch] text-[length:var(--fs-section)] leading-[1.12] tracking-[-0.015em]">
            <span className="text-fg-3">You know the positions you take.</span>{' '}
            <span className="metal">Start there.</span>
          </h2>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link href="/demo" className="btn-metal">Open the demo</Link>
            <Link href="/register" className="btn-quiet">Create an account</Link>
          </div>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-line py-10">
      <div className="wrap flex flex-col gap-6 text-[0.95rem] text-fg-2 md:flex-row md:items-center md:justify-between">
        <Wordmark />
        <nav aria-label="Footer" className="flex flex-wrap gap-x-8 gap-y-2">
          <Link href="/demo" className="hover:text-white">Demo</Link>
          <Link href="/login" className="hover:text-white">Sign in</Link>
          <Link href="/register" className="hover:text-white">Create an account</Link>
          <a href="https://github.com/fatinm1/ClausePilot" className="hover:text-white">Source on GitHub</a>
        </nav>
      </div>
    </footer>
  )
}

export default function LandingPage() {
  const [active, setActive] = useState(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter(Boolean) as HTMLElement[]
    const on = () => {
      const mid = window.innerHeight * 0.45
      let idx = 0
      els.forEach((el, i) => {
        if (el.getBoundingClientRect().top <= mid) idx = i
      })
      setActive(idx)
      const max = document.documentElement.scrollHeight - window.innerHeight
      setProgress(max > 0 ? window.scrollY / max : 0)
    }
    on()
    window.addEventListener('scroll', on, { passive: true })
    return () => window.removeEventListener('scroll', on)
  }, [])

  return (
    <div className="min-h-screen bg-black text-white">
      <a href="#rules" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-full focus:bg-white focus:px-4 focus:py-2 focus:text-black">
        Skip to content
      </a>
      <SiteHeader />
      <ScreenRail active={active} progress={progress} />
      <main>
        <Hero />
        <Sequence />
        <Specimen />
        <Process />
        <Output />
        <Close />
      </main>
      <Footer />
    </div>
  )
}
