'use client';

import { useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Monster as MonsterType, StarPosition, Level } from '@/lib/types';
import { isStarCovered } from '@/lib/gameLogic';

const MONSTER_COLORS: Record<MonsterType['color'], { bg: string; shadow: string; face: string; border: string }> = {
  pink: {
    bg: 'from-pink-400 to-pink-500',
    shadow: 'shadow-pink-300',
    face: '😊',
    border: 'border-pink-300',
  },
  blue: {
    bg: 'from-blue-400 to-blue-500',
    shadow: 'shadow-blue-300',
    face: '😄',
    border: 'border-blue-300',
  },
  green: {
    bg: 'from-emerald-400 to-emerald-500',
    shadow: 'shadow-emerald-300',
    face: '😁',
    border: 'border-emerald-300',
  },
  yellow: {
    bg: 'from-amber-400 to-amber-500',
    shadow: 'shadow-amber-300',
    face: '🤩',
    border: 'border-amber-300',
  },
  purple: {
    bg: 'from-purple-400 to-purple-500',
    shadow: 'shadow-purple-300',
    face: '😎',
    border: 'border-purple-300',
  },
};

interface GameBoardProps {
  level: Level;
  monsters: MonsterType[];
  onSwipe?: (direction: import('@/lib/types').Direction) => void;
  isComplete: boolean;
}

export default function GameBoard({ level, monsters, isComplete }: GameBoardProps) {
  const boardRef = useRef<HTMLDivElement>(null);
  const [cellSize, setCellSize] = useState(0);

  // Calculate cell size based on container
  const measuredRef = useCallback((node: HTMLDivElement | null) => {
    if (node) {
      const size = Math.floor(Math.min(node.offsetWidth, node.offsetHeight) / level.gridSize);
      setCellSize(size);
    }
  }, [level.gridSize]);

  const gridPx = cellSize * level.gridSize;

  return (
    <div
      ref={boardRef}
      className="flex items-center justify-center w-full h-full"
      style={{ minHeight: '300px' }}
    >
      <div
        ref={measuredRef}
        className="relative"
        style={{
          width: gridPx || '100%',
          height: gridPx || 'auto',
          aspectRatio: '1',
        }}
      >
        {cellSize > 0 && (
          <>
            {/* Grid cells */}
            {Array.from({ length: level.gridSize }, (_, row) =>
              Array.from({ length: level.gridSize }, (_, col) => {
                const covered = isStarCovered({ row, col }, monsters);
                const hasStar = level.stars.some((s: StarPosition) => s.row === row && s.col === col);
                return (
                  <div
                    key={`${row}-${col}`}
                    className="absolute border border-white/10 rounded-lg"
                    style={{
                      left: col * cellSize,
                      top: row * cellSize,
                      width: cellSize - 2,
                      height: cellSize - 2,
                      background: 'rgba(255,255,255,0.05)',
                    }}
                  >
                    {hasStar && (
                      <motion.div
                        className="absolute inset-0 flex items-center justify-center"
                        animate={covered ? { scale: [1, 1.3, 0.8], opacity: [1, 1, 0] } : { scale: [1, 1.05, 1] }}
                        transition={covered ? { duration: 0.4 } : { duration: 1.5, repeat: Infinity }}
                      >
                        <span
                          style={{ fontSize: cellSize * 0.45 }}
                          className="select-none"
                        >
                          ⭐
                        </span>
                      </motion.div>
                    )}
                  </div>
                );
              })
            )}

            {/* Monsters */}
            <AnimatePresence>
              {monsters.map((monster) => {
                const style = MONSTER_COLORS[monster.color];
                const width = (monster.colEnd - monster.colStart + 1) * cellSize - 4;
                const height = (monster.rowEnd - monster.rowStart + 1) * cellSize - 4;
                const left = monster.colStart * cellSize + 2;
                const top = monster.rowStart * cellSize + 2;
                const isLarge = width > cellSize * 1.5 || height > cellSize * 1.5;
                const faceSize = Math.min(width, height) * 0.45;

                return (
                  <motion.div
                    key={monster.id}
                    layout
                    layoutId={monster.id}
                    className={`absolute bg-gradient-to-br ${style.bg} rounded-2xl border-2 ${style.border} shadow-lg ${style.shadow} flex items-center justify-center select-none cursor-pointer`}
                    style={{ left, top, width, height }}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    whileHover={{ scale: 1.03 }}
                    whileTap={{ scale: 0.97 }}
                  >
                    {/* Shine effect */}
                    <div className="absolute inset-0 rounded-2xl overflow-hidden">
                      <div className="absolute top-0 left-0 right-0 h-1/3 bg-white/20 rounded-t-2xl" />
                    </div>
                    {/* Face */}
                    <span
                      className="relative z-10 leading-none"
                      style={{ fontSize: faceSize }}
                    >
                      {style.face}
                    </span>
                    {/* Jelly dots for larger monsters */}
                    {isLarge && (
                      <div className="absolute inset-0 flex items-end justify-center pb-1 gap-0.5">
                        {Array.from({ length: Math.min(3, Math.floor(width / cellSize)) }).map((_, i) => (
                          <div
                            key={i}
                            className="rounded-full bg-white/30"
                            style={{ width: faceSize * 0.2, height: faceSize * 0.2 }}
                          />
                        ))}
                      </div>
                    )}
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {/* Win overlay */}
            {isComplete && (
              <motion.div
                className="absolute inset-0 rounded-2xl flex items-center justify-center"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                style={{ background: 'rgba(255,255,255,0.1)' }}
              >
                <motion.div
                  animate={{ scale: [1, 1.1, 1], rotate: [0, 5, -5, 0] }}
                  transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 1 }}
                  className="text-5xl"
                >
                  🎉
                </motion.div>
              </motion.div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
