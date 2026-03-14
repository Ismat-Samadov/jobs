'use client';

import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useGame, useHighScores } from '@/hooks/useGame';
import { useKeyboard, useSwipe } from '@/hooks/useControls';
import { useSound } from '@/hooks/useSound';
import { LEVELS } from '@/lib/levels';
import { Level, Direction } from '@/lib/types';
import GameBoard from '@/components/game/GameBoard';
import Controls from '@/components/game/Controls';
import HUD from '@/components/ui/HUD';
import WinScreen from '@/components/ui/WinScreen';
import PauseMenu from '@/components/ui/PauseMenu';
import LevelSelect from '@/components/ui/LevelSelect';

type Screen = 'levelSelect' | 'game';

export default function Home() {
  const [screen, setScreen] = useState<Screen>('levelSelect');
  const { state, move, undo, reset, togglePause, loadLevel } = useGame(LEVELS[0]);
  const { soundEnabled, toggleSound, play } = useSound();
  const scores = useHighScores();

  const handleMove = useCallback(
    (direction: Direction) => {
      if (state.isComplete || state.isPaused) return;
      move(direction);
      play('slide');
    },
    [move, play, state.isComplete, state.isPaused]
  );

  const handleUndo = useCallback(() => {
    undo();
    play('undo');
  }, [undo, play]);

  const handleReset = useCallback(() => {
    reset();
    play('click');
  }, [reset, play]);

  const handleLevelSelect = useCallback(
    (level: Level) => {
      loadLevel(level);
      setScreen('game');
      play('click');
    },
    [loadLevel, play]
  );

  const handleNextLevel = useCallback(() => {
    const next = LEVELS.find((l) => l.id === state.currentLevel.id + 1);
    if (next) {
      loadLevel(next);
      play('click');
    }
  }, [state.currentLevel.id, loadLevel, play]);

  const handleBack = useCallback(() => {
    setScreen('levelSelect');
    play('click');
  }, [play]);

  // Play win sound when complete
  useEffect(() => {
    if (state.isComplete) {
      play('win');
    }
  }, [state.isComplete, play]);

  // Keyboard controls
  useKeyboard({
    onMove: handleMove,
    onUndo: handleUndo,
    onReset: handleReset,
    onPause: togglePause,
    disabled: screen !== 'game',
  });

  // Swipe controls
  useSwipe({
    onMove: handleMove,
    disabled: screen !== 'game' || state.isComplete || state.isPaused,
  });

  const bestScore = scores.find((s) => s.levelId === state.currentLevel.id);

  return (
    <main
      className="min-h-screen w-full flex flex-col items-center overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
        minHeight: '100dvh',
      }}
    >
      {/* Animated background orbs */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none" aria-hidden>
        {[
          { color: 'rgba(139,92,246,0.15)', top: '10%', left: '10%', size: 300 },
          { color: 'rgba(236,72,153,0.1)', top: '60%', right: '5%', size: 250 },
          { color: 'rgba(59,130,246,0.1)', bottom: '10%', left: '20%', size: 200 },
        ].map((orb, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full blur-3xl"
            style={{
              background: orb.color,
              width: orb.size,
              height: orb.size,
              top: (orb as { top?: string }).top,
              left: (orb as { left?: string }).left,
              right: (orb as { right?: string }).right,
              bottom: (orb as { bottom?: string }).bottom,
            }}
            animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
            transition={{ duration: 4 + i, repeat: Infinity, ease: 'easeInOut', delay: i * 1.5 }}
          />
        ))}
      </div>

      <AnimatePresence mode="wait">
        {screen === 'levelSelect' ? (
          <motion.div
            key="levelSelect"
            className="w-full flex-1 flex flex-col"
            initial={{ opacity: 0, x: -40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -40 }}
            transition={{ duration: 0.3 }}
          >
            <LevelSelect
              onSelect={handleLevelSelect}
              currentLevelId={state.currentLevel.id}
            />
          </motion.div>
        ) : (
          <motion.div
            key="game"
            className="w-full flex-1 flex flex-col items-center justify-between p-3 gap-3 max-w-lg mx-auto"
            initial={{ opacity: 0, x: 40 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 40 }}
            transition={{ duration: 0.3 }}
            style={{ minHeight: '100dvh' }}
          >
            {/* HUD */}
            <div className="w-full">
              <HUD
                level={state.currentLevel}
                moves={state.moves}
                onUndo={handleUndo}
                onReset={handleReset}
                onPause={togglePause}
                onBack={handleBack}
                soundEnabled={soundEnabled}
                onToggleSound={toggleSound}
                canUndo={state.history.length > 0}
              />
            </div>

            {/* Game Board */}
            <div className="flex-1 w-full flex items-center justify-center">
              <div className="w-full max-w-[min(100vw-1.5rem,480px)] aspect-square">
                <GameBoard
                  level={state.currentLevel}
                  monsters={state.monsters}
                  isComplete={state.isComplete}
                />
              </div>
            </div>

            {/* Mobile Controls */}
            <div className="w-full pb-safe">
              <Controls
                onMove={handleMove}
                disabled={state.isComplete || state.isPaused}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Win Screen */}
      <AnimatePresence>
        {state.isComplete && screen === 'game' && (
          <WinScreen
            level={state.currentLevel}
            moves={state.moves}
            bestMoves={bestScore?.moves ?? null}
            onRestart={handleReset}
            onNextLevel={handleNextLevel}
            onLevelSelect={handleBack}
          />
        )}
      </AnimatePresence>

      {/* Pause Menu */}
      <AnimatePresence>
        {state.isPaused && !state.isComplete && screen === 'game' && (
          <PauseMenu
            onResume={togglePause}
            onRestart={handleReset}
            onLevelSelect={handleBack}
            soundEnabled={soundEnabled}
            onToggleSound={toggleSound}
          />
        )}
      </AnimatePresence>
    </main>
  );
}
