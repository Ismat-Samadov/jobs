'use client';

import { motion } from 'framer-motion';
import { RotateCcw, Undo2, Pause, Volume2, VolumeX, ChevronLeft } from 'lucide-react';
import { Level } from '@/lib/types';

interface HUDProps {
  level: Level;
  moves: number;
  onUndo: () => void;
  onReset: () => void;
  onPause: () => void;
  onBack: () => void;
  soundEnabled: boolean;
  onToggleSound: () => void;
  canUndo: boolean;
}

const DIFFICULTY_COLOR: Record<string, string> = {
  easy: 'text-emerald-400',
  medium: 'text-amber-400',
  hard: 'text-red-400',
};

export default function HUD({
  level,
  moves,
  onUndo,
  onReset,
  onPause,
  onBack,
  soundEnabled,
  onToggleSound,
  canUndo,
}: HUDProps) {
  const rating =
    moves === 0
      ? null
      : moves <= level.par
      ? '⭐⭐⭐'
      : moves <= level.par * 1.5
      ? '⭐⭐'
      : '⭐';

  return (
    <div className="flex flex-col gap-2 w-full">
      {/* Top row */}
      <div className="flex items-center justify-between gap-2">
        <motion.button
          className="flex items-center gap-1 px-3 py-2 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-white/80 hover:text-white hover:bg-white/20 transition-colors text-sm"
          whileTap={{ scale: 0.95 }}
          onClick={onBack}
        >
          <ChevronLeft size={16} />
          Levels
        </motion.button>

        <div className="flex-1 text-center">
          <div className="text-white font-bold text-sm truncate">{level.name}</div>
          <div className={`text-xs capitalize font-medium ${DIFFICULTY_COLOR[level.difficulty]}`}>
            {level.difficulty} · Level {level.id}
          </div>
        </div>

        <div className="flex gap-1.5">
          <motion.button
            className="p-2 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-white/80 hover:bg-white/20 transition-colors"
            whileTap={{ scale: 0.9 }}
            onClick={onToggleSound}
            aria-label="Toggle sound"
          >
            {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
          </motion.button>
          <motion.button
            className="p-2 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 text-white/80 hover:bg-white/20 transition-colors"
            whileTap={{ scale: 0.9 }}
            onClick={onPause}
            aria-label="Pause"
          >
            <Pause size={18} />
          </motion.button>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex gap-2">
          <motion.button
            className={`flex items-center gap-1 px-3 py-1.5 rounded-xl text-sm font-medium transition-colors ${
              canUndo
                ? 'bg-white/10 border border-white/20 text-white hover:bg-white/20'
                : 'bg-white/5 border border-white/10 text-white/30 cursor-not-allowed'
            }`}
            whileTap={canUndo ? { scale: 0.95 } : {}}
            onClick={canUndo ? onUndo : undefined}
            disabled={!canUndo}
            aria-label="Undo"
          >
            <Undo2 size={14} />
            Undo
          </motion.button>
          <motion.button
            className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white/10 border border-white/20 text-white text-sm font-medium hover:bg-white/20 transition-colors"
            whileTap={{ scale: 0.95 }}
            onClick={onReset}
            aria-label="Reset"
          >
            <RotateCcw size={14} />
            Reset
          </motion.button>
        </div>

        <div className="text-right">
          <div className="text-white font-bold text-lg leading-none">{moves}</div>
          <div className="text-white/50 text-xs">moves {rating ?? `(par ${level.par})`}</div>
        </div>
      </div>
    </div>
  );
}
