# Morphic Design System

## VSCode-Inspired Product Experience System

---

# 1. Brand Foundation

## Brand Name

**Morphic**

## Brand Personality

Morphic feels like a precision-built developer cockpit fused with a cinematic operating system.

Keywords:

* Technical
* Adaptive
* Intelligent
* Modular
* Focused
* Elegant
* Industrial
* Minimal
* Fast
* Ambient

## Experience Philosophy

The interface should feel:

* Like a programmable workspace
* Quiet, not loud
* Dense but never cluttered
* Productive under long usage sessions
* Keyboard-first
* Motion-light but responsive
* Dark-mode native
* Built for engineers, analysts, creators, and operators

The design language should resemble:

* VSCode
* Linear
* Raycast
* GitHub Dark
* Figma Dev Mode
* Modern terminal environments

---

# 2. Core Visual Identity

## Design Direction

### Style Keywords

* Neo-industrial
* Ambient dark UI
* Precision spacing
* Thin separators
* Frosted overlays
* Glass + matte hybrid
* Terminal-inspired typography
* Layered workspace panels

## Visual Characteristics

* Rounded corners only where meaningful
* Sharp layouts with soft interaction states
* Minimal gradients
* Subtle glows
* Thin borders
* Dense information layouts
* Monospaced accents
* Floating command surfaces

---

# 3. Color System

# Primary Palette

## Core Backgrounds

| Token         | Value               | Usage                |
| ------------- | ------------------- | -------------------- |
| bg.primary    | #0D1117             | Main app background  |
| bg.secondary  | #111827             | Panels               |
| bg.tertiary   | #161B22             | Elevated cards       |
| bg.quaternary | #1C2128             | Interactive surfaces |
| bg.overlay    | rgba(13,17,23,0.82) | Modals and overlays  |

## Sidebar & Navigation

| Token          | Value   |
| -------------- | ------- |
| nav.background | #0B0F14 |
| nav.hover      | #1A1F29 |
| nav.active     | #212734 |
| nav.border     | #2B3240 |

## Accent Colors

| Token            | Value   | Usage            |
| ---------------- | ------- | ---------------- |
| accent.primary   | #3B82F6 | Main brand blue  |
| accent.secondary | #8B5CF6 | Purple highlight |
| accent.success   | #10B981 | Success states   |
| accent.warning   | #F59E0B | Warnings         |
| accent.error     | #EF4444 | Errors           |
| accent.info      | #06B6D4 | Info             |

## Text Colors

| Token          | Value   |
| -------------- | ------- |
| text.primary   | #E6EDF3 |
| text.secondary | #9DA7B3 |
| text.tertiary  | #6B7280 |
| text.inverse   | #0D1117 |
| text.link      | #58A6FF |

## Border Colors

| Token            | Value   |
| ---------------- | ------- |
| border.primary   | #2D333B |
| border.secondary | #21262D |
| border.focus     | #3B82F6 |
| border.hover     | #4B5563 |

## Status Colors

| Status  | Background | Text    | Border  |
| ------- | ---------- | ------- | ------- |
| Success | #052E1A    | #4ADE80 | #166534 |
| Warning | #3B2400    | #FBBF24 | #92400E |
| Error   | #3B0A0A    | #F87171 | #991B1B |
| Info    | #082F49    | #38BDF8 | #0369A1 |

---

# 4. Typography System

## Primary Font

### Inter

Usage:

* Main UI text
* Forms
* Navigation
* Buttons
* Tables
* Cards

Weights:

* 400 Regular
* 500 Medium
* 600 Semibold
* 700 Bold

## Monospace Font

### JetBrains Mono

Usage:

* Code
* IDs
* Logs
* Command palettes
* Data visualization
* Terminal areas
* AI responses

Weights:

* 400
* 500
* 600

## Alternative Font Stack

font-family:

```css
Inter, system-ui, sans-serif
```

Monospace:

```css
JetBrains Mono, Consolas, monospace
```

---

# 5. Typography Scale

| Token    | Size | Weight | Usage            |
| -------- | ---- | ------ | ---------------- |
| text-xs  | 12px | 400    | Metadata         |
| text-sm  | 13px | 400    | Secondary text   |
| text-md  | 14px | 400    | Default UI text  |
| text-lg  | 16px | 500    | Body emphasis    |
| text-xl  | 18px | 600    | Section headings |
| text-2xl | 22px | 600    | Major sections   |
| text-3xl | 28px | 700    | Page titles      |
| text-4xl | 36px | 700    | Landing hero     |

## Line Heights

| Token          | Value |
| -------------- | ----- |
| leading-tight  | 1.2   |
| leading-normal | 1.5   |
| leading-loose  | 1.8   |

---

# 6. Spacing System

Based on 4px grid.

| Token    | Value |
| -------- | ----- |
| space-1  | 4px   |
| space-2  | 8px   |
| space-3  | 12px  |
| space-4  | 16px  |
| space-5  | 20px  |
| space-6  | 24px  |
| space-8  | 32px  |
| space-10 | 40px  |
| space-12 | 48px  |
| space-16 | 64px  |

---

# 7. Radius System

| Token      | Value |
| ---------- | ----- |
| radius-xs  | 4px   |
| radius-sm  | 6px   |
| radius-md  | 8px   |
| radius-lg  | 12px  |
| radius-xl  | 16px  |
| radius-2xl | 24px  |

Usage:

* Buttons: 8px
* Inputs: 8px
* Cards: 12px
* Modals: 16px
* Floating panels: 16px

---

# 8. Elevation & Shadows

## Shadow Tokens

### shadow-sm

```css
0 1px 2px rgba(0,0,0,0.12)
```

### shadow-md

```css
0 4px 12px rgba(0,0,0,0.24)
```

### shadow-lg

```css
0 10px 30px rgba(0,0,0,0.32)
```

### shadow-glow

```css
0 0 0 1px rgba(59,130,246,0.2),
0 0 20px rgba(59,130,246,0.18)
```

---

# 9. Motion System

## Motion Philosophy

Motion should feel:

* Mechanical
* Instant
* Smooth but restrained
* Functional
* Low-latency

## Animation Timing

| Token   | Value |
| ------- | ----- |
| instant | 80ms  |
| fast    | 140ms |
| normal  | 220ms |
| slow    | 320ms |

## Easing

```css
cubic-bezier(0.2, 0.8, 0.2, 1)
```

## Motion Rules

* Avoid bounce animations
* Use opacity + translate transitions
* Never animate large layout shifts
* Use micro interactions only
* Prefer fade and scale

---

# 10. Iconography System

## Icon Library

### Google Material Symbols Rounded

Recommended:

* Material Symbols Rounded
* Material Symbols Sharp for dense tooling

## Icon Sizes

| Token    | Value |
| -------- | ----- |
| icon-xs  | 14px  |
| icon-sm  | 16px  |
| icon-md  | 18px  |
| icon-lg  | 20px  |
| icon-xl  | 24px  |
| icon-2xl | 32px  |

## Recommended Icons

### Navigation

* dashboard
* grid_view
* home
* terminal
* folder
* code
* settings
* search
* tune
* widgets

### Actions

* add
* edit
* delete
* close
* more_horiz
* more_vert
* refresh
* download
* upload
* content_copy

### AI / Smart Features

* auto_awesome
* smart_toy
* psychology
* lightbulb
* memory
* bolt
* analytics

### Data & Monitoring

* monitoring
* timeline
* query_stats
* database
* dns
* storage
* cloud

### User & Team

* person
* group
* badge
* account_circle

## Icon Styling Rules

* Default opacity: 0.82
* Hover opacity: 1
* Use stroke-based icons
* Avoid filled icons except alerts
* Use 18px for default app actions

---

# 11. Layout System

## App Shell Layout

### Structure

```text
┌──────────────────────────────┐
│ Top Activity Bar             │
├───────┬──────────────────────┤
│ Side  │ Main Workspace       │
│ Bar   │                      │
│       │                      │
├───────┴──────────────────────┤
│ Bottom Status Bar            │
└──────────────────────────────┘
```

## Layout Regions

### Activity Sidebar

Width: 64px
Purpose:

* Global navigation
* Workspace switching
* AI launcher
* Notifications

### Explorer Sidebar

Width: 280px
Purpose:

* Navigation tree
* Context tools
* Filters
* Resources

### Main Workspace

Flexible
Purpose:

* Content
* Dashboards
* Editors
* AI chat
* Data tables

### Secondary Panel

Width: 360px
Purpose:

* Inspector
* Logs
* Assistant
* Properties

### Bottom Status Bar

Height: 28px
Purpose:

* Connectivity
* Branch
* Environment
* Runtime status

---

# 12. Component System

# Buttons

## Primary Button

* Background: accent.primary
* Text: white
* Radius: 8px
* Height: 36px
* Padding: 12px 16px

Hover:

* Slight brightness increase
* Glow border

## Secondary Button

* Transparent background
* Border: border.primary
* Hover: bg.quaternary

## Ghost Button

* No border
* Background on hover only

## Danger Button

* Background: accent.error

## Icon Button

* Square
* 32px / 36px / 40px variants

---

# Inputs

## Text Input

Height: 38px

States:

* Default
* Hover
* Focus
* Error
* Disabled

Features:

* Optional leading icon
* Optional trailing actions
* Inline validation

## Search Input

Features:

* Command palette aesthetic
* Rounded background
* Search icon
* Keyboard hint chip

---

# Dropdowns

Style:

* Floating panel
* Matte background
* Thin border
* Keyboard navigable
* Dense spacing

---

# Checkboxes

Style:

* Rounded-square
* Blue fill when active
* Smooth scale transition

---

# Radio Buttons

Style:

* Minimal circles
* Thin stroke
* Subtle glow on active

---

# Switches

Style:

* Compact
* Pill shape
* Soft animated thumb

---

# Tabs

## Editor Tabs

Inspired by VSCode.

Features:

* Active underline
* File icons
* Close action
* Drag reorder

---

# Cards

## Standard Card

* Elevated background
* Thin border
* Radius 12px
* Padding 16px

## Interactive Card

* Hover elevation
* Glow border
* Cursor pointer

## Analytics Card

Includes:

* Metric title
* Value
* Delta
* Graph area

---

# Tables

## Data Table

Features:

* Sticky headers
* Virtualized rows
* Dense mode
* Sortable columns
* Resizable columns
* Keyboard navigation
* Row selection

Style:

* Alternating row hover
* Minimal borders
* Monospaced data cells

---

# Modals

## Modal Style

* Frosted backdrop
* Center aligned
* Soft fade animation
* Radius 16px
* Dense header actions

Sizes:

* sm 400px
* md 600px
* lg 900px
* xl 1200px

---

# Drawers

Slide from:

* Right
* Left
* Bottom

Use for:

* Inspectors
* Settings
* AI panels

---

# Toast Notifications

Position:

* Bottom right

Features:

* Auto dismiss
* Status icon
* Progress indicator

---

# Tooltips

Style:

* Minimal dark overlay
* 12px font
* 6px radius
* Instant appearance

---

# Context Menus

Essential for Morphic.

Features:

* Keyboard support
* Nested actions
* Command labels
* Shortcut hints

---

# Accordions

Use for:

* Settings groups
* Debug panels
* Logs
* Nested data

---

# Breadcrumbs

Style:

* Compact
* Slash separators
* Interactive nodes

---

# Badges

Variants:

* Success
* Warning
* Error
* Neutral
* AI
* Beta

---

# Avatars

Sizes:

* 24
* 32
* 40
* 48
* 64

Support:

* Presence indicator
* Role color ring

---

# Command Palette

Critical component.

Inspired by:

* VSCode
* Raycast

Features:

* Global keyboard access
* AI actions
* Search everything
* Keyboard shortcuts
* Action previews

Shortcut:

```text
Ctrl + K
```

Style:

* Floating centered overlay
* Glass background
* Search-first UX

---

# 13. AI UX Patterns

## AI Chat Panel

Features:

* Streaming responses
* Markdown rendering
* Code blocks
* Prompt history
* File references
* Inline actions

## AI Message Styling

User:

* Neutral background

Assistant:

* Slight elevated background
* Accent border

## AI Actions

* Explain
* Refactor
* Generate
* Summarize
* Analyze
* Debug

---

# 14. Navigation Design

## Sidebar Navigation

Structure:

* Workspace switcher
* Primary sections
* Favorites
* Pinned items
* Settings

Interaction:

* Hover expansion
* Collapsible groups
* Smooth active indicators

---

# 15. Data Visualization

## Chart Style

Charts should be:

* Minimal
* Grid-light
* Dark-native
* High contrast

## Chart Colors

| Usage          | Color   |
| -------------- | ------- |
| Primary line   | #3B82F6 |
| Secondary line | #8B5CF6 |
| Success        | #10B981 |
| Warning        | #F59E0B |
| Error          | #EF4444 |

## Recommended Libraries

* Recharts
* Apache ECharts
* Tremor

---

# 16. Accessibility Standards

## Accessibility Goals

* WCAG AA minimum
* Full keyboard support
* Visible focus states
* Screen reader support
* Reduced motion support

## Focus State

```css
outline: 2px solid #3B82F6;
outline-offset: 2px;
```

---

# 17. Responsive Design Rules

## Breakpoints

| Token | Value  |
| ----- | ------ |
| sm    | 640px  |
| md    | 768px  |
| lg    | 1024px |
| xl    | 1280px |
| 2xl   | 1536px |

## Mobile Strategy

* Collapse sidebars
* Bottom navigation
* Fullscreen overlays
* Larger touch targets

---

# 18. Dark Mode Strategy

Morphic should be:

* Dark-first
* Light mode secondary

## Dark UI Rules

* Avoid pure black
* Use layered surfaces
* Use opacity-based depth
* Keep contrast readable

---

# 19. Empty States

Style:

* Minimal illustration
* Helpful guidance
* Primary action
* AI suggestions

Tone:

* Calm
* Technical
* Helpful

---

# 20. Loading States

## Skeleton Loaders

* Animated shimmer
* Low contrast
* Preserve layout

## Inline Loaders

* Thin progress bars
* Small spinners
* Terminal dots

---

# 21. Error States

Features:

* Clear explanation
* Retry action
* Expandable technical details
* Error code copy action

---

# 22. Notification System

Notification Types:

* System
* AI
* Deployment
* Monitoring
* Security
* Collaboration

Priority Levels:

* Info
* Important
* Critical

---

# 23. Keyboard UX

## Keyboard-First Rules

Everything important must be keyboard accessible.

## Recommended Shortcuts

| Action          | Shortcut |
| --------------- | -------- |
| Command Palette | Ctrl+K   |
| Search          | Ctrl+P   |
| New Item        | Ctrl+N   |
| Toggle Sidebar  | Ctrl+B   |
| Settings        | Ctrl+,   |

---

# 24. Micro Interactions

## Hover Effects

* Slight elevation
* Border illumination
* Soft background tint

## Active States

* Accent underline
* Subtle inset glow

## Drag & Drop

* Magnetic highlights
* Layered overlays
* Animated placeholders

---

# 25. Recommended Tech Stack

## Frontend

* React
* Next.js
* TypeScript
* TailwindCSS
* Framer Motion

## UI Libraries

* shadcn/ui
* Radix UI
* TanStack Table

## State Management

* Zustand
* Redux Toolkit
* React Query

---

# 26. CSS Variable Tokens

```css
:root {
  --bg-primary: #0D1117;
  --bg-secondary: #111827;
  --accent-primary: #3B82F6;
  --text-primary: #E6EDF3;
  --border-primary: #2D333B;
  --radius-md: 8px;
  --shadow-md: 0 4px 12px rgba(0,0,0,0.24);
}
```

---

# 27. Tailwind Theme Extension

```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        morphic: {
          bg: '#0D1117',
          panel: '#161B22',
          accent: '#3B82F6'
        }
      }
    }
  }
}
```

---

# 28. Design Principles Summary

## Morphic Must Feel

* Fast
* Intelligent
* Structured
* Ambient
* Technical
* Quietly futuristic

## Avoid

* Oversized UI
* Bright gradients
* Excessive blur
* Cartoon visuals
* Heavy neumorphism
* Oversaturated colors
* Massive spacing

---

# 29. Signature Morphic Experience

The user should feel like they are:

* Operating a modern digital control system
* Navigating intelligent workspaces
* Using a programmable environment
* Inside a focused engineering cockpit

The interface should disappear into the workflow like a dark glass exoskeleton around cognition.

---

# 30. Final Design DNA

## Morphic =

VSCode precision
+
Linear elegance
+
Raycast velocity
+
GitHub developer familiarity
+
AI-native interaction patterns
+
Operational dashboard density

A workspace designed for deep work, rapid iteration, and intelligent systems orchestration.
