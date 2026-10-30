---
name: NewsLens India Investigative Intelligence
colors:
  surface: '#f8f9ff'
  surface-dim: '#d0daee'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff3ff'
  surface-container: '#e6eeff'
  surface-container-high: '#dfe9fc'
  surface-container-highest: '#d9e3f6'
  on-surface: '#121c2a'
  on-surface-variant: '#42474d'
  inverse-surface: '#273140'
  inverse-on-surface: '#ebf1ff'
  outline: '#73777e'
  outline-variant: '#c2c7ce'
  surface-tint: '#41617e'
  primary: '#00253d'
  on-primary: '#ffffff'
  primary-container: '#183b56'
  on-primary-container: '#85a5c5'
  inverse-primary: '#a9caeb'
  secondary: '#00696d'
  on-secondary: '#ffffff'
  secondary-container: '#9af1f5'
  on-secondary-container: '#007074'
  tertiary: '#341e00'
  on-tertiary: '#ffffff'
  tertiary-container: '#523100'
  on-tertiary-container: '#d79439'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#cde5ff'
  primary-fixed-dim: '#a9caeb'
  on-primary-fixed: '#001d32'
  on-primary-fixed-variant: '#284a65'
  secondary-fixed: '#9af1f5'
  secondary-fixed-dim: '#7ed4d8'
  on-secondary-fixed: '#002021'
  on-secondary-fixed-variant: '#004f52'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#121c2a'
  surface-variant: '#d9e3f6'
typography:
  headline-xl:
    fontFamily: Newsreader
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
  headline-xl-mobile:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-lg:
    fontFamily: Newsreader
    fontSize: 28px
    fontWeight: '500'
    lineHeight: 36px
  headline-lg-mobile:
    fontFamily: Newsreader
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 30px
  headline-md:
    fontFamily: Newsreader
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 28px
  headline-sm:
    fontFamily: Newsreader
    fontSize: 18px
    fontWeight: '500'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system embodies the clinical rigor of investigative journalism, open-source intelligence (OSINT), and institutional policy research. Designed for analysts, journalists, and media researchers monitoring misinformation across the Indian media ecosystem, the visual language avoids the sensationalism and alarmist tropes common in digital news feeds. 

The aesthetic is grounded in high-density clarity, academic sobriety, and analytical restraint. It replaces simplistic binary indicators ("Fake" vs. "True") with granular evidentiary assessments, nuanced confidence intervals, and verifiable forensic metadata. Visual artifacts favor structured data tables, typographic clarity, subtle tonal separation, and archival-grade density. The interface projects quiet authority, intellectual transparency, and absolute objectivity.

## Colors

The palette establishes an austere, research-first environment designed for prolonged visual inspection without cognitive fatigue.

- **Primary Navy (`#183B56`)**: Anchors critical structural chrome, formal navigation bars, institutional headings, and primary research actions.
- **Secondary Teal (`#167C80`)**: Applied to analytical pivots, verified entities, deep-dive telemetry, cross-referenced citation links, and active filtering tags.
- **Caution / Warning Amber (`#B7791F`)**: Indicates evidentiary anomalies, disputed claims, narrative shifts, or unverified claims. This deliberately avoids garish reds, maintaining scientific neutrality.
- **Neutral Dark (`#182230`)**: Used for all high-contrast primary text, metric integers, and tabular values.
- **Secondary Neutral (`#667085`)**: Applied to datestamps, sourcing chains, tabular headers, secondary annotations, and inactive state icons.
- **Surface Canvas (`#F6F8FA`)**: The base background for the overall platform, establishing soft contrast against work surfaces.
- **Surface Layer (`#FFFFFF`)**: Base white used strictly for content containers, evidence dossiers, query inputs, and data inspection panels.
- **Subtle Backdrops**:
  - `Informational Background (`#EEF4F7`)`: Tonal backing for contextual summaries, methodology callouts, and system disclaimers.
  - `Subtle Teal Background (`#EAF5F3`)`: Tonal backing for cross-reference badges, provenance confirmations, and stable signals.
- **Structural Border (`#E4E7EC`)**: Neutral hair-line separation dividing data cells, panels, and structural partitions.

## Typography

The typographical pairing reinforces investigative credibility. Headings utilize `Newsreader`, an editorial serif that imparts the authority of established print journalism and institutional whitepapers. Body text, interface labels, metrics, and forensic logs rely on `Inter` for hyper-legible, pixel-precise data scanning.

- **Newsreader (Headings)**: Reserved for dossier titles, narrative briefs, analytical summaries, and primary section headers. Letterforms should remain optical and natural, avoiding tight letter spacing.
- **Inter (Body & Interface)**: Applied to all news excerpts, evidentiary transcripts, search inputs, data grids, and UI states. Tabular numbers (`tnum`) must be enforced across all quantitative data visualizations and timestamp trackers.
- **Monospace Reference (Optional Utility)**: For cryptographic hash validation, raw URL extractions, and broadcast ingest logs, use an unstyled native tabular system font (`ui-monospace`, `monospace`) at 12px with high contrast.

## Layout & Spacing

The layout system is tailored for analytical dashboards and narrative investigation spaces, accommodating Streamlit-compatible structural layouts and dense split-screen analysis.

- **Desktop Layout (≥ 1200px)**: A 12-column responsive fluid grid with fixed outer gutters (`1.5rem`) and max-width safety constraints (`1440px`). Supports asymmetrical split screens: 4-column filter/monitoring stream paired with an 8-column investigative workbench or deep forensic audit ledger.
- **Tablet Layout (768px – 1199px)**: An 8-column fluid structure. Collapses multi-pane sidebars into persistent top-docked toolbars or stacked analytical panels with uniform `1rem` gutters.
- **Mobile Layout (< 768px)**: A 4-column flow prioritizing linear feed triage, compact alert summaries, and nested expanders for forensic details.
- **Spacing Rhythm**: Spacing strictly reflects logical encapsulation. Micro data points (tags, author, time) cluster tightly via `space-xs` and `space-sm`. Components and tabular rows expand cleanly with `space-md`. Entire analytical dossiers and verification blocks isolate with `space-lg` and `space-xl`.

## Elevation & Depth

Visual hierarchy does not rely on deep drop shadows or skeuomorphic elevation. Depth is achieved via **low-contrast outlines** and **tonal layering**, emulating precision instrumentation and curated print documents.

- **Surface Layering**: The foundational canvas rests at `#F6F8FA`. Dossiers, query interfaces, and data matrices sit directly atop it as `#FFFFFF` planes bordered by a precise `1px solid #E4E7EC`.
- **Nested Compartments**: Inner sub-analyses (such as provenance logs, quote verification snippets, or linguistic anomaly matrices) use `#EEF4F7` or `#EAF5F3` with flush borders, avoiding elevation shifts altogether.
- **Shadow Treatment**: Avoid floating shadows. In the rare event of flyout source inspector panels or dropdown auto-completes, apply a crisp ambient shadow: `0 4px 12px rgba(24, 59, 86, 0.06)`, keeping blur low and avoiding dark spreads.

## Shapes

The design uses an architectural, crisp visual cadence with subtle softening to maintain screen legibility. 

- **Containers & Cards**: Base `0.25rem` (4px) corner radius. Structural modules feel grounded and rectangular, avoiding friendly, consumer-style bubbles.
- **Badges & Metadata Tags**: Base `0.25rem` (4px) corner radius. Never fully round into pill formats; metadata must feel like archival catalog stamps.
- **Dividers & Boundaries**: Crisp, straight 1px rules across all structural axes, reinforcing a tabular, ledger-like aesthetic.

## Components

### Buttons & Interactive Triggers
- **Primary Action (Run Pipeline / Export Audit)**: Solid `#183B56` background, `#FFFFFF` text, `4px` border radius, padding `0.5rem 1rem`. Active state scales down opacity to 90%; no elevation lift.
- **Secondary Action (Filter / Inspect Provenance)**: Transparent background, `1px solid #E4E7EC`, `#182230` text. Hover shifts background to `#EEF4F7`.
- **Pivot Action (Investigate Entity)**: Text-link styled trigger in `#167C80` with semi-bold weight and subtle hover underline.

### Metadata Badges & Evidence Tags
- **Strictly Non-Binary**: Never use generic "Real" or "Fake" labels. Use structured descriptors: `Corroborated`, `Disputed Context`, `Unverified Source`, `Manipulated Media`.
- **Visual Spec**: Compact typography (`label-sm`), uppercase or title-case, padding `2px 8px`, `4px` corner radius.
  - *Standard Context*: Background `#EEF4F7`, text `#183B56`, border `1px solid #D0DCE3`.
  - *Corroborated / Verified*: Background `#EAF5F3`, text `#167C80`, border `1px solid #C4E3DF`.
  - *Disputed / Cautionary*: Background `#FEF7ED`, text `#B7791F`, border `1px solid #F6D8A8`.

### Investigative Data Tables & Streamlit Displays
- **Headers**: Upper-case `label-sm`, background `#F6F8FA`, text `#667085`, bottom border `2px solid #E4E7EC`.
- **Data Rows**: Padding `0.75rem 1rem`, alternating subtle zebra-striping optional but preferred clean white with `1px solid #E4E7EC` bottom border.
- **Metrics & Numbers**: Set in `Inter` with `font-variant-numeric: tabular-nums`.

### Cards & Evidence Panels
- **Structure**: `#FFFFFF` background, `1px solid #E4E7EC`, `4px` corner radius, internal padding `1.25rem`.
- **Article Brief Card**: Clean headline in `Newsreader` (`headline-sm` or `headline-md`), immediate publication source and regional timestamp in `body-sm` (`#667085`), followed by a compact analysis drawer displaying corroborated quotes and claim lineage.

### Input Fields & Filter Bars
- **Fields**: Background `#FFFFFF`, border `1px solid #E4E7EC`, focus outline `2px solid #167C80` (offset 1px). Text `#182230`, placeholder `#667085`.
- **Streamlit Controls**: Custom dropdown selectors, date ranges, and entity sliders use flat white surfaces, crisp borders, and dark teal indicators for selected intervals.

### Transparent Evidence Dossier Panel
- Dedicated collapsible drawer or split-view pane detailing the raw claim extraction, linguistic sentiment distribution, verified domain history, and cross-referenced Indian news agency citations (ANI, PTI, regional wire services) without sensationalist framing.