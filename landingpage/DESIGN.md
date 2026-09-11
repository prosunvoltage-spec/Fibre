# Design System: KYL Landing

**Source of structure:** primefold.ai (layout rhythm, typographic architecture, container
language, motion restraint). **Colors and content are NOT taken from the reference** — the
palette below is KYL's own.

**Reading note:** values marked `~` are measured from screenshots at a ~1900px viewport and
are proportional targets, not pixel-exact reproductions.

---

## Configuration — Set Your Style

| Dial | Level | Meaning here |
|------|-------|--------------|
| **Creativity** | `5` | Clean with personality. The character comes from scale contrast and photography, not from typographic tricks. |
| **Density** | `3` | Gallery-airy. Sections are separated by large empty bands; nothing is packed. |
| **Variance** | `4` | Subtle offsets. Section layouts rotate (split, centered, grid, full-bleed carousel) but the grid stays predictable. |
| **Motion Intent** | `3` | Restrained. Movement answers a click. No scroll choreography. |

---

## 1. Visual Theme & Atmosphere

Quiet, spacious, editorial-corporate. The page reads as a sequence of calm, generously spaced
bands, each carrying exactly one idea. Confidence comes from scale contrast: very large
headlines against small, quiet supporting text, with wide empty margins doing the framing.

Surfaces float. Navigation, cards and media blocks sit as rounded containers on the page
rather than filling it edge to edge, which gives every element an intentional boundary.

What makes the reference read as expensive, and what this system keeps:

1. **Photography as the primary surface.** Dark, tonally deep photographs carry the hero
   instead of gradients or illustration. Text sits on the photograph, never beside it.
2. **Whitespace between bands is larger than expected** — roughly the height of a headline
   block sits empty above each section heading.
3. **One type family throughout.** Hierarchy is built from size, weight and color only.
4. **A single radius language.** Nav pill, cards, media blocks and buttons all belong to the
   same curvature family.
5. **Hairline borders instead of shadows.** Elevation is suggested by a 1px near-transparent
   line and a color shift, not by a drop shadow.
6. **Credible interface fragments.** Where a product is shown, it is a real screen detail at
   real proportions, not a decorative mock.
7. **Restraint in accent use.** Accent color appears in small marks only, never as a large
   colored surface.

---

## 2. Color Palette & Roles

Structure adopted from the reference, values are KYL's.

- **Page White** (`#FFFFFF`) — Primary background for content bands
- **Quiet Surface** (`#F4F4F5`) — Alternating band background and input fill
- **Ink** (`#14161A`) — Primary text, dark bands, solid buttons. Never pure black
- **Ink Muted** (`#6B6F76`) — Body copy, descriptions, metadata
- **Hairline** (`#E6E7EA`) — 1px structural lines, card borders, table rules
- **Signal Blue** (`#0071E3`) — The single accent. Links, primary button fill, small marks
- **Signal Blue Deep** (`#005BB8`) — Hover and pressed state of the accent
- **Signal Tint** (`#E9F2FD`) — Accent used as a quiet background, e.g. behind a check icon
- **Media Scrim** (`rgba(11,17,24,0.88)` → `rgba(11,17,24,0)`) — Horizontal gradient over
  photography so text stays legible on the left third

### Constraints
- Exactly **one** accent. It never covers a large area.
- Never pure black. Ink is `#14161A`.
- One neutral temperature throughout. No warm gray next to cool gray.
- Text on photography always sits on a directional scrim, never on the raw image.

### Banned
- Purple or violet gradients, neon glows, "AI" iridescence
- Decorative gradient washes as section backgrounds
- More than one accent hue per page

---

## 3. Typography Rules

One family, weight-driven hierarchy, tight tracking at large sizes.

- **Family:** `Hanken Grotesk` (self-hosted). Acceptable substitutes with the same character:
  `Geist`, `Satoshi`, `General Sans`. `Inter` is banned — it is the default tell.
- **Display / H1:** `clamp(2.75rem, 5.6vw, 5rem)`, weight `800`, tracking `-0.03em`,
  leading `1.05`. Sentence case, ends in a period. Never more than two lines.
- **Section H2:** `clamp(2rem, 3.9vw, 2.75rem)`, weight `800`, tracking `-0.03em`,
  leading `1.08`. Two lines maximum, broken by meaning, not by the container.
- **Card title / H3:** `1.1875rem`, weight `700`, tracking `-0.015em`
- **Lead paragraph:** `clamp(1.0625rem, 1.4vw, 1.1875rem)`, weight `400`, leading `1.6`,
  color Ink Muted, max `52ch`
- **Body:** `1.0625rem`, leading `1.6`, max `65ch`
- **Meta / label:** `0.9375rem`, weight `600`
- **Eyebrow:** `0.75rem`, weight `700`, tracking `0.1em`, uppercase, set inside a pill with a
  hairline border and a 6px accent dot. **Maximum two per page.** The reference proves the
  quieter alternative works: sentence case, no pill, a small mark before the words.

### Rules
- Hierarchy comes from size, weight and color. Not from caps, not from color-splitting a word.
- Line length never exceeds 65 characters for body, 52 for lead.
- No typographic label above a heading that already names the thing.

### Banned
- `Inter`, `Roboto`, `Arial` as the display family
- Generic serifs (`Times New Roman`, `Georgia`, `Garamond`)
- Em dashes `—` anywhere in page copy
- Accenting a single word inside a headline by color or italic, unless the brief demands it

---

## 4. Component Stylings

- **Navigation:** A floating pill bar, `~72px` tall, white, `border-radius: 999px` or
  `~20px`, inset `~16px` from the viewport edge, hairline border, sits above content.
  Logo left, links centered, two actions right: one outlined pill, one solid Ink pill.
  Single line at desktop. Height never exceeds 80px.
- **Primary button:** Solid Ink or Signal Blue, `border-radius: 999px`, `~48px` tall,
  `padding: 0 24px`, weight `600`. Optional trailing circle containing an arrow.
- **Secondary button:** Transparent with a `1.5px` border. On photography the border is
  `rgba(255,255,255,0.6)`, on white it is Hairline.
- **Card:** `border-radius: ~16px`, Page White on a Quiet Surface band, hairline border,
  **no shadow**. Internal media block gets its own `~12px` radius and sits inset from the
  card edge. Content order: media, then title, then two lines of text.
- **Media block:** `border-radius: ~20px`, `overflow: hidden`, objects fill the frame.
  Full-bleed hero media gets `~28px`.
- **Floating chip row:** Small labelled tiles overlapping the bottom edge of the hero media,
  translucent over the photograph, one of them solid white to mark the active item.
- **Input:** Quiet Surface fill, `border-radius: ~10px`, `1.5px` transparent border that
  turns Signal Blue on focus. Label always above the field, never a placeholder as label.
- **Carousel:** Peeking neighbours on both sides so the row is visibly wider than the
  viewport. Circular white arrow buttons, dot pagination beneath. Keyboard reachable.

---

## 5. Hero Section

- Full-bleed photograph as the surface, `~28px` radius if inset, square if edge to edge.
- Directional scrim from the text side, not a uniform darkening of the whole image.
- Text block left-aligned, starting at `~6%` of the viewport width, vertically centered,
  maximum width `~830px`.
- Order: small kicker line, two-line headline, lead paragraph, two buttons.
- The hero fits the first viewport. Top padding never exceeds the nav height plus `~64px`.
- A row of product or service chips overlaps the lower edge of the media.

### Banned in the hero
- "Scroll down" text, bouncing chevrons, scroll arrows
- Centered hero text when variance is above 4
- Text overlapping other text or sitting on unscrimmed photography

---

## 6. Layout Principles

- **Container:** `max-width: 1360px`, centered, side padding `24px` mobile, `48px` desktop.
- **Spacing scale:** 8-point. `8 / 16 / 24 / 32 / 48 / 64 / 96 / 128`.
- **Band rhythm:** vertical padding of `96px` mobile and `128–160px` desktop between
  sections. The empty space above a section heading is deliberately larger than the space
  between heading and content.
- **Section head:** heading left, one explanatory sentence right, both sharing a baseline at
  desktop; stacked at mobile.
- **Alternation:** background alternates Page White and Quiet Surface. No two adjacent
  sections use the same layout shape. Order used by the reference: split hero → quiet proof
  row → centered statement with one large panel → three-column grid → full-bleed carousel.
- **Grid:** 3 columns desktop, 2 at `700px`, 1 below. Grids never leave an empty cell; if the
  item count does not divide, widen the first and last item instead.
- **Logo / proof row:** wordmarks only, no boxes, no grayscale filter, wide even spacing,
  minimal vertical padding.

---

## 7. Responsive Rules

- Mobile first. Breakpoints at `700px`, `900px`, `1024px`.
- Headline scale drops through `clamp()`, never through separate mobile markup.
- Nav collapses to a logo plus a menu button at `1000px`; the overlay covers the page and
  locks background scroll.
- Multi-column grids stack in source order. Carousels become swipeable rows.
- No horizontal scrolling anywhere except inside a container that is explicitly a carousel.
- Interactive targets are at least `24px` on web, `44px` where the primary audience is mobile,
  with at least `8px` between adjacent targets.

---

## 8. Motion & Interaction

Movement is rare and always earns its place.

- **One page-load moment:** the hero assembles once, children staggered by `~90ms`,
  `700ms`, ease `cubic-bezier(0.25, 0.1, 0.25, 1)`, translating `14px` upward while fading in.
  Nothing else animates on load.
- **No scroll-triggered reveals.** Sections are present when reached.
- **User-triggered only, everywhere else:** carousel advance, menu open, focus, hover on
  genuinely interactive elements.
- **Shared durations:** `--dur-fast 200ms` for color and focus, `--dur-base 300ms` for menu
  and nav state, `--dur-slow 700ms` for media zoom and the hero entrance.
- **Animate `transform` and `opacity` only.**
- `prefers-reduced-motion: reduce` disables the hero entrance and all transitions.

> **Open item:** the reference's scroll behaviour could not be observed, only its structure.
> The carousels imply user-triggered horizontal movement. If the reference does animate on
> scroll, this section is deliberately quieter than the original.

---

## 9. Anti-Patterns (Banned)

- Fade-and-slide-up entrance on every section
- Hover lift plus shadow on cards that are not links
- An arrow badge or chevron on an element that navigates nowhere
- One radius for every element regardless of size or hierarchy
- The same soft gray shadow under every card
- Tracked-out uppercase eyebrows above every heading
- Meta strings joined by middle dots
- Em dashes in page copy
- Three identical feature cards as the only section shape
- Invented numbers, fake ratings, placeholder review counts presented as real
- Pure black, purple neon, multi-accent palettes
- Centered hero text combined with a centered everything-else page
