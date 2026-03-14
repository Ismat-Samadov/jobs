'use client';

import { motion } from 'framer-motion';
import { RotateCcw, ChevronRight, Star, Trophy } from 'lucide-react';
import { Level } from '@/lib/types';
import { LEVELS } from '@/lib/levels';

interface WinScreenProps {
  level: Level;
  moves: number;
  bestMoves: number | null;
  onRestart: () => void;
  onNextLevel: () => void;
  onLevelSelect: () => void;
}

function Stars({ moves, par }: { moves: number; par: number }) {
  const count = moves <= par ? 3 : moves <= Math.ceil(par * 1.5) ? 2 : 1;
  return (
    <div className="flex gap-1 justify-center">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          initial={{ scale: 0, rotate: -30 }}
          animate={{ scale: i < count ? 1 : 0.5, rotate: 0, opacity: i < count ? 1 : 0.3 }}
          transition={{ delay: 0.3 + i * 0.15, type: 'spring', stiffness: 400 }}
        >
          <Star
            size={32}
            className={i < count ? 'text-yellow-400 fill-yellow-400' : 'text-gray-500 fill-gray-600'}
          />
        </motion.div>
      ))}
    </div>
  );
}

export default function WinScreen({
  level,
  moves,
  bestMoves,
  onRestart,
  onNextLevel,
  onLevelSelect,
}: WinScreenProps) {
  const isNewBest = bestMoves === null || moves <= bestMoves;
  const hasNext = LEVELS.find((l) => l.id === level.id + 1);

  return (
    <motion.div
      className="fixed inset-0 flex items-center justify-center z-50 p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}
    >
      <motion.div
        className="relative bg-gradient-to-br from-violet-900/90 to-purple-900/90 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl p-8 max-w-sm w-full text-center"
        initial={{ scale: 0.7, y: 40 }}
        animate={{ scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25, delay: 0.1 }}
      >
        {/* Confetti circles */}
        {[...Array(8)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              width: 8 + (i % 3) * 4,
              height: 8 + (i % 3) * 4,
              background: ['#f472b6', '#60a5fa', '#34d399', '#fbbf24', '#a78bfa'][i % 5],
              left: `${10 + (i * 11) % 80}%`,
              top: `${5 + (i * 17) % 30}%`,
            }}
            animate={{
              y: [-20, 20, -20],
              x: [-5, 5, -5],
              opacity: [0.8, 1, 0.8],
            }}
            transition={{
              duration: 2 + (i % 3) * 0.5,
              repeat: Infinity,
              delay: i * 0.2,
            }}
          />
        ))}

        <motion.div
          className="text-5xl mb-3"
          animate={{ rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] }}
          transition={{ duration: 1, repeat: Infinity, repeatDelay: 1 }}
        >
          🎊
        </motion.div>

        <h2 className="text-2xl font-bold text-white mb-1">Level Complete!</h2>
        <p className="text-white/60 text-sm mb-4">{level.name}</p>

        <Stars moves={moves} par={level.par} />

        <div className="mt-4 mb-6 flex justify-center gap-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-white">{moves}</div>
            <div className="text-white/50 text-xs">moves</div>
          </div>
          <div className="w-px bg-white/20" />
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{level.par}</div>
            <div className="text-white/50 text-xs">par</div>
          </div>
          {bestMoves && (
            <>
              <div className="w-px bg-white/20" />
              <div className="text-center">
                <div className={`text-2xl font-bold ${isNewBest ? 'text-emerald-400' : 'text-white'}`}>
                  {isNewBest ? moves : bestMoves}
                </div>
                <div className="text-white/50 text-xs flex items-center gap-0.5 justify-center">
                  {isNewBest && <Trophy size={10} className="text-emerald-400" />}
                  best
                </div>
              </div>
            </>
          )}
        </div>

        {isNewBest && (
          <motion.div
            className="mb-4 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/40 rounded-full text-emerald-400 text-sm font-medium inline-block"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.8 }}
          >
            🏆 New Best!
          </motion.div>
        )}

        <div className="flex flex-col gap-2">
          {hasNext && (
            <motion.button
              className="w-full py-3 rounded-2xl bg-gradient-to-r from-violet-500 to-purple-600 text-white font-bold shadow-lg flex items-center justify-center gap-2 hover:from-violet-400 hover:to-purple-500 transition-all"
              whileTap={{ scale: 0.97 }}
              onClick={onNextLevel}
            >
              Next Level <ChevronRight size={18} />
            </motion.button>
          )}
          <div className="flex gap-2">
            <motion.button
              className="flex-1 py-2.5 rounded-2xl bg-white/10 border border-white/20 text-white font-medium flex items-center justify-center gap-1.5 hover:bg-white/20 transition-colors"
              whileTap={{ scale: 0.97 }}
              onClick={onRestart}
            >
              <RotateCcw size={16} /> Retry
            </motion.button>
            <motion.button
              className="flex-1 py-2.5 rounded-2xl bg-white/10 border border-white/20 text-white font-medium hover:bg-white/20 transition-colors"
              whileTap={{ scale: 0.97 }}
              onClick={onLevelSelect}
            >
              Levels
            </motion.button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
