# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Deal teams and attorneys: in-house or family-office deal teams and small-firm lawyers who receive inbound NDAs from counterparties and need to mark them up against their own house positions before signing. They are reviewers, not drafters. They want a Word file with tracked changes that a counterparty's lawyer will accept as normal, and they do not want to retype the same five edits on every NDA.

Secondary audience: people looking at the product as a portfolio piece (recruiters, engineers). They are served by the same honest product story; the UI does not speak to them separately.

## Product Purpose

ClausePilot takes an uploaded NDA (.docx), applies the firm's standard redlining rules, and returns a Word document with real tracked changes (insertions and deletions the reviewer can accept or reject in Word). Success: a reviewer uploads an NDA, picks rules, reviews proposed changes, and downloads a redline they would send without re-editing.

## Positioning

Rules come first: an admin writes the firm's positions once (cap the confidentiality term, add investors/agents/financing sources to Representatives, add a retention carve-out, fill firm details and signature block), and every NDA is redlined against them. AI (a chain of OpenAI-compatible providers: Groq, Gemini, OpenRouter free tiers, then OpenAI if a key is set; rule-based fallback) proposes edits inside those rules; the output is native Word tracked changes, not a PDF or a diff view.

## Operating Context

- Input: counterparty NDAs as .docx only.
- Two roles: ADMIN creates and manages rules and users; USER uploads documents, selects rules, reviews changes, uploads a signature image, downloads the redline.
- Review step: proposed changes are shown with accept/reject before the final document is generated.
- Output opens in Microsoft Word with Track Changes.

## Capabilities and Constraints

- Stack: Next.js 14 static export (web/) served by a Flask API (api/), Postgres, deployed on Railway.
- Terminology: "redline", "tracked changes", "rules", "NDA", "counterparty".
- Confirmed true: role-based access (admin vs user); HTTPS in transit (Railway).
- Confirmed false, must not be claimed: automatic 24-hour deletion (deletion is manual only), end-to-end encryption, audit logging. "No training on your documents" is not a product guarantee and must not be claimed.

## Brand Commitments

- Name: ClausePilot (replaces the old in-app name "NDA Redline").
- Visual reference chosen by the owner: erinys.ai (dark, metallic serif, tracked-change "redline" motif). Use its design language only; none of its brand, copy, logo, or imagery.

## Evidence on Hand

- No customers, testimonials, logos, metrics, or case studies exist. Do not fabricate any.
- Real material: the rule set in the codebase, the demo route (/demo), sample/test .docx files in the repo, and the 60s demo video on the owner's portfolio.
- Client documents from past work must never appear in the product, screenshots, or copy.

## Product Principles

1. Show the redline, not a promise: tracked changes are the product, so the UI demonstrates them literally.
2. The firm's rules are the authority; AI works inside them.
3. Claim only what the code does.
4. Built for a reviewer at a desk: dense, legible, keyboard-friendly working screens.
