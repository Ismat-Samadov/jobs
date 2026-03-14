'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

type SoundName = 'slide' | 'merge' | 'win' | 'click' | 'undo';

// Simple synthesized sounds using Web Audio API
function createAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  return new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
}

function playTone(
  ctx: AudioContext,
  frequency: number,
  duration: number,
  type: OscillatorType = 'sine',
  volume = 0.3
) {
  const oscillator = ctx.createOscillator();
  const gainNode = ctx.createGain();

  oscillator.connect(gainNode);
  gainNode.connect(ctx.destination);

  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, ctx.currentTime);
  oscillator.frequency.exponentialRampToValueAtTime(frequency * 0.8, ctx.currentTime + duration);

  gainNode.gain.setValueAtTime(volume, ctx.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

  oscillator.start(ctx.currentTime);
  oscillator.stop(ctx.currentTime + duration);
}

function playSlideSound(ctx: AudioContext) {
  playTone(ctx, 300, 0.1, 'sine', 0.2);
}

function playMergeSound(ctx: AudioContext) {
  playTone(ctx, 520, 0.15, 'sine', 0.3);
  setTimeout(() => playTone(ctx, 660, 0.15, 'sine', 0.3), 80);
}

function playWinSound(ctx: AudioContext) {
  const notes = [523, 659, 784, 1047];
  notes.forEach((freq, i) => {
    setTimeout(() => playTone(ctx, freq, 0.3, 'sine', 0.4), i * 150);
  });
}

function playClickSound(ctx: AudioContext) {
  playTone(ctx, 400, 0.05, 'square', 0.1);
}

function playUndoSound(ctx: AudioContext) {
  playTone(ctx, 400, 0.1, 'sine', 0.2);
  setTimeout(() => playTone(ctx, 300, 0.1, 'sine', 0.2), 60);
}

export function useSound() {
  const [soundEnabled, setSoundEnabled] = useState(true);
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem('pudding-sound');
    if (saved !== null) setSoundEnabled(saved === 'true');
  }, []);

  const getCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = createAudioContext();
    }
    // Resume if suspended (browser autoplay policy)
    if (audioCtxRef.current?.state === 'suspended') {
      audioCtxRef.current.resume();
    }
    return audioCtxRef.current;
  }, []);

  const play = useCallback(
    (sound: SoundName) => {
      if (!soundEnabled) return;
      const ctx = getCtx();
      if (!ctx) return;

      try {
        switch (sound) {
          case 'slide': playSlideSound(ctx); break;
          case 'merge': playMergeSound(ctx); break;
          case 'win': playWinSound(ctx); break;
          case 'click': playClickSound(ctx); break;
          case 'undo': playUndoSound(ctx); break;
        }
      } catch {
        // Ignore audio errors
      }
    },
    [soundEnabled, getCtx]
  );

  const toggleSound = useCallback(() => {
    setSoundEnabled((prev) => {
      const next = !prev;
      localStorage.setItem('pudding-sound', String(next));
      return next;
    });
  }, []);

  return { soundEnabled, toggleSound, play };
}
