import Link from 'next/link'

export function Wordmark({ className = '', href = '/' }: { className?: string; href?: string }) {
  return (
    <Link
      href={href}
      aria-label="ClausePilot home"
      className={`font-display text-[1.7rem] leading-none tracking-[-0.01em] text-white ${className}`}
    >
      <span className="metal">ClausePilot</span>
    </Link>
  )
}

/** Authored outline of stacked contract sheets, stroked in brushed metal. Decorative.
 *  Animates once on mount (pages fan out, outline draws, lines write, redlines strike,
 *  signature signs), then the redlines re-mark on a slow loop. */
export function PaperSheets({ className = '', id = 'ps', animate = true }: { className?: string; id?: string; animate?: boolean }) {
  let n = 0
  const lines = (x: number, y: number, count: number, w: number, start: number) =>
    Array.from({ length: count }, (_, i) => {
      const len = i % 5 === 4 ? w * 0.55 : i % 3 === 2 ? w * 0.86 : w
      const d = start + i * 0.07
      n++
      return (
        <line
          key={i}
          className="ps-draw"
          pathLength={1}
          style={{ ['--d' as string]: `${d}s`, ['--t' as string]: '0.45s' }}
          x1={x}
          y1={y + i * 16}
          x2={x + len}
          y2={y + i * 16}
        />
      )
    })
  const draw = (d: number, t: number) => ({ ['--d' as string]: `${d}s`, ['--t' as string]: `${t}s` })
  const sheet = 'M70 40h250l40 40v440H70z'
  return (
    <svg viewBox="0 0 420 560" className={`${animate ? 'ps-anim' : ''} ${className}`} aria-hidden="true" fill="none">
      <defs>
        <linearGradient id={`${id}-m`} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="420" y2="560">
          <stop offset="0" stopColor="#8e9196" />
          <stop offset=".3" stopColor="#ffffff" />
          <stop offset=".5" stopColor="#a9acb1" />
          <stop offset=".72" stopColor="#f6f7f9" />
          <stop offset="1" stopColor="#5c5f63" />
        </linearGradient>
      </defs>
      <g stroke={`url(#${id}-m)`} strokeWidth="1.2" strokeLinejoin="round">
        <g className="ps-fan" style={{ ['--x' as string]: '-36px', ['--y' as string]: '-22px', ['--d' as string]: '0.15s' }}>
          <path d={sheet} opacity=".28" />
        </g>
        <g className="ps-fan" style={{ ['--x' as string]: '-18px', ['--y' as string]: '-11px', ['--d' as string]: '0.05s' }}>
          <path d={sheet} opacity=".5" />
        </g>
        <path d={sheet} className="ps-draw" pathLength={1} style={draw(0.1, 1.1)} />
        <path d="M320 40v40h40" className="ps-draw" pathLength={1} style={draw(1.05, 0.35)} />
      </g>
      <g stroke={`url(#${id}-m)`} strokeWidth="1" opacity=".55">
        {lines(104, 120, 9, 220, 1.1)}
        {lines(104, 290, 8, 220, 1.5)}
      </g>
      <g strokeWidth="2.4" strokeLinecap="round" stroke="#b04545">
        <line x1="104" y1="184" x2="230" y2="184" className="ps-red" pathLength={1} style={{ ['--d' as string]: '2.25s' }} />
        <line x1="104" y1="338" x2="300" y2="338" opacity=".8" className="ps-red" pathLength={1} style={{ ['--d' as string]: '2.6s' }} />
      </g>
      <g stroke={`url(#${id}-m)`} strokeWidth="1.2" strokeLinecap="round">
        <line x1="104" y1="476" x2="250" y2="476" opacity=".6" className="ps-draw" pathLength={1} style={draw(2.85, 0.4)} />
        <path d="M104 460c20-14 34 10 52-4s30-10 44 2" className="ps-draw" pathLength={1} style={draw(3.05, 0.9)} />
      </g>
    </svg>
  )
}

export function SectionMark({ className = '' }: { className?: string }) {
  return (
    <span aria-hidden="true" className={`font-display ${className}`}>
      §
    </span>
  )
}
