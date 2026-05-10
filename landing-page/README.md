# Morphic Landing Page

A modern, production-ready landing page for Morphic - an AI-powered incident intelligence platform.

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **Animations**: Framer Motion
- **Icons**: Lucide React

## Features

- **Modern Design**: Neo-industrial dark UI inspired by Linear, Vercel, and GitHub
- **Animations**: Smooth scroll reveals, hover effects, and interactive elements
- **Responsive**: Mobile-first design that works on all devices
- **Performance**: Optimized for fast load times and smooth interactions
- **Accessibility**: WCAG 2.1 AA compliant with keyboard navigation support

## Sections

1. **Hero Section**: Animated terminal demonstration with floating metrics
2. **Integration Bar**: Tech stack logos with hover effects
3. **Features Grid**: 8 core capabilities with glass-morphism cards
4. **AI Pipeline**: 4-layer architecture visualization
5. **Chaos Engineering**: 5 failure scenario cards
6. **Knowledge Graph**: Neo4j topology visualization
7. **Live Demo**: Interactive terminal simulation
8. **Architecture Map**: Complete system diagram
9. **API Showcase**: Endpoint documentation
10. **CTA Section**: Deployment call-to-action

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
landing-page/
├── src/
│   ├── components/
│   │   ├── HeroTerminal.tsx
│   │   ├── PipelineFlow.tsx
│   │   ├── ChaosScenarios.tsx
│   │   ├── KnowledgeGraph.tsx
│   │   ├── LiveDemoTerminal.tsx
│   │   ├── ArchitectureMap.tsx
│   │   ├── APIShowcase.tsx
│   │   └── index.ts
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

## Design System

### Colors

- **Background**: `#0D1117` (Primary), `#111827` (Secondary)
- **Accent**: `#3B82F6` (Blue), `#8B5CF6` (Purple)
- **Status**: `#10B981` (Success), `#F59E0B` (Warning), `#EF4444` (Error)
- **Text**: `#E6EDF3` (Primary), `#9DA7B3` (Secondary)
- **Border**: `#2D333B`

### Typography

- **Primary**: Inter (400, 500, 600, 700)
- **Monospace**: JetBrains Mono (code, logs, IDs)

### Spacing

Based on 4px grid system with consistent 8px, 16px, 24px, 32px, 48px, 64px increments.

## License

MIT License - see LICENSE file for details.

---

Built with ❤️ for the Morphic project.
