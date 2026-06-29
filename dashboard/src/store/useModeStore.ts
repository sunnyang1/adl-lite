import { create } from 'zustand';
import { SystemMode } from '@/api/types';

interface ModeState {
  currentMode: SystemMode;
  nMin: number;
  devMode: boolean;
  setMode: (mode: SystemMode, nMin: number, devMode: boolean) => void;
}

export const useModeStore = create<ModeState>((set) => ({
  currentMode: 'moderate',
  nMin: 3,
  devMode: false,
  setMode: (mode: SystemMode, nMin: number, devMode: boolean) =>
    set({ currentMode: mode, nMin: nMin, devMode: devMode }),
}));
