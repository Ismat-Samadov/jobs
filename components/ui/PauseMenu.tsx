'use client';

import { motion } from 'framer-motion';
import { Play, RotateCcw, ChevronLeft, Volume2, VolumeX } from 'lucide-react';

interface PauseMenuProps {
  onResume: () => void;
  onRestart: () => void;
  onLevelSelect: () => void;
  soundEnabled: boolean;
  onToggleSound: () => void;
}

export default function PauseMenu({
  onResume,
  onRestart,
  onLevelSelect,
  soundEnabled,
  onToggleSound,
}: PauseMenuProps) {
  return (
    <motion.div
      className="fixed inset-0 flex items-center justify-center z-50 p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(8px)' }}
    >
      <motion.div
        className="bg-gradient-to-br from-slate-900/90 to-violet-900/90 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl p-8 max-w-xs w-full text-center"
        initial={{ scale: 0.8, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
      >
        <div className="text-4xl mb-4">⏸️</div>
        <h2 className="text-2xl font-bold text-white mb-6">Paused</h2>

        <div className="flex flex-col gap-3">
          <motion.button
            className="w-full py-3 rounded-2xl bg-gradient-to-r from-violet-500 to-purple-600 text-white font-bold shadow-lg flex items-center justify-center gap-2 hover:from-violet-400 hover:to-purple-500 transition-all"
            whileTap={{ scale: 0.97 }}
            onClick={onResume}
          >
            <Play size={18} /> Resume
          </motion.button>

          <motion.button
            className="w-full py-3 rounded-2xl bg-white/10 border border-white/20 text-white font-medium flex items-center justify-center gap-2 hover:bg-white/20 transition-colors"
            whileTap={{ scale: 0.97 }}
            onClick={onToggleSound}
          >
            {soundEnabled ? <Volume2 size={18} /> : <VolumeX size={18} />}
            Sound: {soundEnabled ? 'On' : 'Off'}
          </motion.button>

          <motion.button
            className="w-full py-3 rounded-2xl bg-white/10 border border-white/20 text-white font-medium flex items-center justify-center gap-2 hover:bg-white/20 transition-colors"
            whileTap={{ scale: 0.97 }}
            onClick={onRestart}
          >
            <RotateCcw size={18} /> Restart Level
          </motion.button>

          <motion.button
            className="w-full py-3 rounded-2xl bg-white/10 border border-white/20 text-white font-medium flex items-center justify-center gap-2 hover:bg-white/20 transition-colors"
            whileTap={{ scale: 0.97 }}
            onClick={onLevelSelect}
          >
            <ChevronLeft size={18} /> Level Select
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}
