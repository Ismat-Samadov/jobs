'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Star, Trophy, Lock, ChevronRight } from 'lucide-react';
import { Level, HighScore, Difficulty } from '@/lib/types';
import { LEVELS } from '@/lib/levels';

interface LevelSelectProps {
  onSelect: (level: Level) => void;
  currentLevelId?: number;
}

const DIFFICULTY_LABELS: Record<Difficulty, string> = {
  easy: '🟢 Easy',
  medium: '🟡 Medium',
  hard: '🔴 Hard',
};

const DIFFICULTY_BG: Record<Difficulty, string> = {
  easy: 'from-emerald-900/50 to-green-900/50 border-emerald-500/30',
  medium: 'from-amber-900/50 to-yellow-900/50 border-amber-500/30',
  hard: 'from-red-900/50 to-rose-900/50 border-red-500/30',
};

function StarRating({ moves, par }: { moves: number; par: number }) {
  const count = moves <= par ? 3 : moves <= Math.ceil(par * 1.5) ? 2 : 1;
  return (
    <div className="flex gap-0.5">
      {[0, 1, 2].map((i) => (
        <Star
          key={i}
          size={12}
          className={i < count ? 'text-yellow-400 fill-yellow-400' : 'text-white/20 fill-white/10'}
        />
      ))}
    </div>
  );
}

export default function LevelSelect({ onSelect, currentLevelId }: LevelSelectProps) {
  const [scores, setScores] = useState<HighScore[]>([]);

  useEffect(() => {
    setScores(JSON.parse(localStorage.getItem('pudding-monsters-scores') || '[]'));
  }, []);

  const difficulties: Difficulty[] = ['easy', 'medium', 'hard'];

  return (
    <div className="flex flex-col gap-6 w-full max-w-lg mx-auto px-4 py-6 overflow-y-auto max-h-screen">
      {/* Header */}
      <div className="text-center">
        <motion.div
          className="text-5xl mb-2"
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        >
          🍮
        </motion.div>
        <h1 className="text-3xl font-black text-white tracking-tight">Pudding Monsters</h1>
        <p className="text-white/50 text-sm mt-1">Slide jelly monsters to cover all the stars!</p>
      </div>

      {/* Levels by difficulty */}
      {difficulties.map((diff) => {
        const diffLevels = LEVELS.filter((l) => l.difficulty === diff);
        return (
          <div key={diff}>
            <div className="text-sm font-bold text-white/60 mb-2 uppercase tracking-widest">
              {DIFFICULTY_LABELS[diff]}
            </div>
            <div className="grid grid-cols-1 gap-2">
              {diffLevels.map((level) => {
                const score = scores.find((s) => s.levelId === level.id);
                const isCurrent = level.id === currentLevelId;
                // First level always unlocked, then unlock if prev completed
                const prevCompleted = level.id === 1 || scores.some((s) => s.levelId === level.id - 1);
                const isLocked = !prevCompleted && !score;

                return (
                  <motion.button
                    key={level.id}
                    className={`relative flex items-center gap-4 p-4 rounded-2xl border bg-gradient-to-r ${DIFFICULTY_BG[diff]} backdrop-blur-sm transition-all ${
                      isLocked
                        ? 'opacity-50 cursor-not-allowed'
                        : isCurrent
                        ? 'ring-2 ring-violet-400 ring-offset-2 ring-offset-transparent'
                        : 'hover:brightness-110 cursor-pointer'
                    }`}
                    whileTap={isLocked ? {} : { scale: 0.98 }}
                    onClick={() => !isLocked && onSelect(level)}
                  >
                    {/* Level number */}
                    <div className="w-10 h-10 rounded-xl bg-white/10 flex items-center justify-center font-bold text-white text-lg flex-shrink-0">
                      {isLocked ? <Lock size={16} /> : level.id}
                    </div>

                    {/* Info */}
                    <div className="flex-1 text-left">
                      <div className="text-white font-semibold text-sm">{level.name}</div>
                      <div className="text-white/50 text-xs mt-0.5">
                        {level.gridSize}×{level.gridSize} grid · par {level.par}
                      </div>
                    </div>

                    {/* Score */}
                    {score && (
                      <div className="flex flex-col items-end gap-0.5">
                        <StarRating moves={score.moves} par={level.par} />
                        <div className="text-white/40 text-xs">{score.moves} moves</div>
                      </div>
                    )}
                    {!score && !isLocked && (
                      <ChevronRight size={16} className="text-white/40" />
                    )}
                  </motion.button>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Total stars */}
      <div className="text-center pb-4">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10">
          <Trophy size={14} className="text-yellow-400" />
          <span className="text-white/60 text-sm">
            {scores.length} / {LEVELS.length} levels completed
          </span>
        </div>
      </div>
    </div>
  );
}
