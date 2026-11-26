# Design

ClausePilot's visual system. The design language follows erinys.ai, chosen by the owner as the reference. The brand, copy and imagery are ClausePilot's own.

## World
A black page holding a marked-up contract. Headlines are set in brushed metal. The one signal colour is redline, and it only ever means "deleted" or "changed". The only ornament is an outline of stacked contract sheets, drawn as authored SVG.

## Color
| Role | Value |
|---|---|
| Ground | `#000` |
| Raised panels | `#0a0a0a` |
| Panel fill | `#121212` |
| Well | `#181818` |
| Text | `#fff` |
| Secondary text | `#a6a6a6` |
| Muted text | `#7a7a7a` |
| Hairlines | `rgba(255,255,255,.12)`, strong `.35` |
| Metal ramp | `#fff` `#f6f7f9` `#cbced2` `#a9acb1` `#8e9196` `#5c5f63` |
| Redline (deletions, errors) | `#b04545` |
| Redline text | `#e58a8a` |
| Redline wash | `rgba(176,69,69,.14)` |
| Ok | `#7fb39a` (success only) |

On the white Word page:
- deletions are `#9b2f2f`, struck through;
- insertions are `#1f3f6b`, underlined.

## Type
- **Display:** Libre Caslon Display 400 (@fontsource), used for headlines only and rendered with the `.metal` text treatment. Caslon is the traditional face of printed law.
- **UI and body:** Inter Variable at weight 380 to 500.
- **Scale:**
  - hero `clamp(2.6rem,6vw,6rem)`
  - scroll statements `clamp(1.75rem,3.4vw,3rem)`
  - section headings `clamp(2rem,3.4vw,3.25rem)`
  - body-lg `clamp(1.05rem,1.35vw,1.3rem)`
- **Line height and tracking:** 1.04–1.12 for display, 1.5 for body. Display tracking is -0.015 to -0.02em.
- **Mixed emphasis:** a section headline pairs a metal clause with a muted clause.

## Components
- **`.btn-metal`:** a 52px pill (40px for `.sm`) whose metallic border wanders over 7.8s. It is the primary action.
- **`.btn-quiet`:** a hairline pill for secondary actions.
- **`.btn-danger`:** a redline outline.
- **`.panel`:** `#0a0a0a`, 1px hairline, 20px radius. This is the only container used on working screens.
- **`.field`:** 48px tall, 12px radius, with a metal focus border and a 3px soft ring.
- **`.tc-del` / `.tc-ins`:** tracked-change styling on dark grounds. `.doc-del` / `.doc-ins` do the same on the white page.
- **App header** (`components/app-header.tsx`): wordmark, section name, role pill, Sign out.
- **Auth shell** (`components/auth-shell.tsx`): form on the left; on the right, a sticky panel with the sheet outline and one tracked-change line.

## Motion
- **Signature moment:** on load, the hero redline draws. The strikethrough goes in about 0.28s, then the insertion fades in from blur and its underline draws.
- **Header:** the wordmark slides from centre to left once the page scrolls, and the nav fades in.
- **Pinned three-line sequence:** inactive lines sit at 0.14 / 0.3 opacity. The last line underlines "redline" and scales up.
- **Left § rail:** shows section progress at 1280px and wider.
- **Background:** the sheet outline drifts (22s) and tilts (16s).
- **Reduced motion:** with `prefers-reduced-motion`, every animation resolves to its end state.

## Detector notes
`impeccable detect` flags two things. Both are kept on purpose:
- **Gradient text (`.metal`):** the owner pinned this as the reference's signature.
- **Inter:** it is the reference's body face and a workhorse for the Operate screens.
