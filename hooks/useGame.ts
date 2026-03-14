'use client';

import { useCallback, useEffect, useReducer } from 'react';
import { Direction, GameState, Level, HighScore } from '@/lib/types';
import { initGameState, applyMove, undoMove } from '@/lib/gameLogic';
import { LEVELS } from '@/lib/levels';

type Action =
  | { type: 'MOVE'; direction: Direction }
  | { type: 'UNDO' }
  | { type: 'RESET' }
  | { type: 'LOAD_LEVEL'; level: Level }
  | { type: 'TOGGLE_PAUSE' }
  | { type: 'SELECT_MONSTER'; id: string | null };

function reducer(state: GameState, action: Action): GameState {
  switch (action.type) {
    case 'MOVE':
      return applyMove(state, action.direction);
    case 'UNDO':
      return undoMove(state);
    case 'RESET':
      return initGameState(state.currentLevel);
    case 'LOAD_LEVEL':
      return initGameState(action.level);
    case 'TOGGLE_PAUSE':
      return { ...state, isPaused: !state.isPaused };
    case 'SELECT_MONSTER':
      return { ...state, selectedMonsterId: action.id };
    default:
      return state;
  }
}

export function useGame(initialLevel?: Level) {
  const [state, dispatch] = useReducer(
    reducer,
    initGameState(initialLevel ?? LEVELS[0])
  );

  const move = useCallback((direction: Direction) => {
    dispatch({ type: 'MOVE', direction });
  }, []);

  const undo = useCallback(() => dispatch({ type: 'UNDO' }), []);
  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);
  const togglePause = useCallback(() => dispatch({ type: 'TOGGLE_PAUSE' }), []);
  const loadLevel = useCallback(
    (level: Level) => dispatch({ type: 'LOAD_LEVEL', level }),
    []
  );
  const selectMonster = useCallback(
    (id: string | null) => dispatch({ type: 'SELECT_MONSTER', id }),
    []
  );

  // Save high score to localStorage when level is completed
  useEffect(() => {
    if (state.isComplete) {
      const key = 'pudding-monsters-scores';
      const existing: HighScore[] = JSON.parse(localStorage.getItem(key) || '[]');
      const levelId = state.currentLevel.id;
      const prev = existing.find((s) => s.levelId === levelId);
      if (!prev || state.moves < prev.moves) {
        const updated = [
          ...existing.filter((s) => s.levelId !== levelId),
          { levelId, moves: state.moves, date: new Date().toISOString() },
        ];
        localStorage.setItem(key, JSON.stringify(updated));
      }
    }
  }, [state.isComplete, state.currentLevel.id, state.moves]);

  return { state, move, undo, reset, togglePause, loadLevel, selectMonster };
}

export function useHighScores(): HighScore[] {
  if (typeof window === 'undefined') return [];
  return JSON.parse(localStorage.getItem('pudding-monsters-scores') || '[]');
}
