'use client';

import { useEffect, useRef } from 'react';
import { Direction } from '@/lib/types';

interface UseControlsOptions {
  onMove: (direction: Direction) => void;
  onUndo: () => void;
  onReset: () => void;
  onPause: () => void;
  disabled?: boolean;
}

export function useKeyboard({
  onMove,
  onUndo,
  onReset,
  onPause,
  disabled,
}: UseControlsOptions) {
  useEffect(() => {
    if (disabled) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowLeft':
        case 'a':
        case 'A':
          e.preventDefault();
          onMove('left');
          break;
        case 'ArrowRight':
        case 'd':
        case 'D':
          e.preventDefault();
          onMove('right');
          break;
        case 'ArrowUp':
        case 'w':
        case 'W':
          e.preventDefault();
          onMove('up');
          break;
        case 'ArrowDown':
        case 's':
        case 'S':
          e.preventDefault();
          onMove('down');
          break;
        case 'z':
        case 'Z':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            onUndo();
          }
          break;
        case 'r':
        case 'R':
          e.preventDefault();
          onReset();
          break;
        case 'p':
        case 'P':
        case 'Escape':
          e.preventDefault();
          onPause();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onMove, onUndo, onReset, onPause, disabled]);
}

export function useSwipe({
  onMove,
  disabled,
}: {
  onMove: (direction: Direction) => void;
  disabled?: boolean;
}) {
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (disabled) return;

    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      touchStartRef.current = { x: touch.clientX, y: touch.clientY };
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (!touchStartRef.current) return;
      const touch = e.changedTouches[0];
      const dx = touch.clientX - touchStartRef.current.x;
      const dy = touch.clientY - touchStartRef.current.y;
      const absDx = Math.abs(dx);
      const absDy = Math.abs(dy);
      const MIN_SWIPE = 30;

      if (Math.max(absDx, absDy) < MIN_SWIPE) return;

      if (absDx > absDy) {
        onMove(dx > 0 ? 'right' : 'left');
      } else {
        onMove(dy > 0 ? 'down' : 'up');
      }

      touchStartRef.current = null;
    };

    window.addEventListener('touchstart', handleTouchStart, { passive: true });
    window.addEventListener('touchend', handleTouchEnd, { passive: true });

    return () => {
      window.removeEventListener('touchstart', handleTouchStart);
      window.removeEventListener('touchend', handleTouchEnd);
    };
  }, [onMove, disabled]);
}
