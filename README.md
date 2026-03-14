# Pudding Monsters

A cute, polished sliding puzzle browser game built with **Next.js 16**, **TypeScript**, and **Tailwind CSS**.

Slide jelly monsters across the grid to merge them and cover all the stars — inspired by the classic Pudding Monsters mobile game.

## Features

- 15 handcrafted levels across 3 difficulty tiers (Easy, Medium, Hard)
- Core mechanics: slide monsters, merge them into bigger blobs, cover all stars
- Star rating system — earn up to 3 stars per level based on move efficiency
- Local high scores saved in localStorage
- Undo — step back through moves freely
- Pause / resume with pause menu
- Synthesized sound effects via Web Audio API (toggle on/off)
- Fully responsive — swipe gestures on mobile, arrow keys on desktop
- Glassmorphism + dark cosmic theme with smooth Framer Motion animations
- Accessible — keyboard navigable, ARIA labels

## Tech Stack

| Tech | Purpose |
|------|---------|
| Next.js 16 (App Router) | Framework |
| TypeScript (strict) | Type safety |
| Tailwind CSS v4 | Styling |
| Framer Motion | Animations |
| Web Audio API | Synthesized sound |
| localStorage | Score persistence |

## Controls

### Desktop
| Key | Action |
|-----|--------|
| Arrow Keys / WASD | Slide monsters |
| Ctrl+Z | Undo |
| R | Reset level |
| P / Escape | Pause |

### Mobile
| Gesture | Action |
|---------|--------|
| Swipe | Slide monsters |
| On-screen D-pad | Directional controls |
| HUD buttons | Undo, Reset, Pause |

## How to Run Locally

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Open http://localhost:3000
```

## Game Rules

1. **Slide** — tap a direction to slide all monsters in that direction
2. **Merge** — two monsters that collide stick together, forming a larger blob
3. **Cover** — a star is covered when it falls inside a monster's bounding area
4. **Win** — cover every star on the board to complete the level
5. **Efficiency** — fewer moves = more stars! Try to match or beat par

## Project Structure

```
├── app/              # Next.js App Router pages
├── components/
│   ├── game/         # GameBoard, Controls
│   └── ui/           # HUD, WinScreen, PauseMenu, LevelSelect
├── hooks/            # useGame, useControls, useSound
├── lib/              # Types, game logic, level definitions
└── public/           # favicon.svg
```
