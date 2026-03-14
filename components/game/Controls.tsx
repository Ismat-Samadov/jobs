'use client';

import { motion } from 'framer-motion';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight } from 'lucide-react';
import { Direction } from '@/lib/types';

interface ControlsProps {
  onMove: (direction: Direction) => void;
  disabled?: boolean;
}

const BTN =
  'flex items-center justify-center w-14 h-14 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/20 text-white shadow-lg active:scale-95 hover:bg-white/20 transition-colors';

export default function Controls({ onMove, disabled }: ControlsProps) {
  return (
    <div className="grid grid-cols-3 gap-2 w-fit mx-auto select-none">
      {/* Up */}
      <div />
      <motion.button
        className={BTN}
        whileTap={{ scale: 0.9 }}
        onPointerDown={() => !disabled && onMove('up')}
        aria-label="Move up"
      >
        <ArrowUp size={24} />
      </motion.button>
      <div />

      {/* Left / Down / Right */}
      <motion.button
        className={BTN}
        whileTap={{ scale: 0.9 }}
        onPointerDown={() => !disabled && onMove('left')}
        aria-label="Move left"
      >
        <ArrowLeft size={24} />
      </motion.button>
      <motion.button
        className={BTN}
        whileTap={{ scale: 0.9 }}
        onPointerDown={() => !disabled && onMove('down')}
        aria-label="Move down"
      >
        <ArrowDown size={24} />
      </motion.button>
      <motion.button
        className={BTN}
        whileTap={{ scale: 0.9 }}
        onPointerDown={() => !disabled && onMove('right')}
        aria-label="Move right"
      >
        <ArrowRight size={24} />
      </motion.button>
    </div>
  );
}
