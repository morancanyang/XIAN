import { create } from 'zustand';
import type { BusEvent } from '@xian/types';

/** 模式二控制台存储：对话流 / 战报卡片 / 能量（技术方案 5 store/consoleStore）。 */
export interface ConsoleState {
  stream: BusEvent[];
  cards: BusEvent[];
  energy: number;
  hintsUsed: string[];
  appendStream: (event: BusEvent) => void;
  appendCard: (event: BusEvent) => void;
  setEnergy: (value: number) => void;
  useHint: (level: string) => void;
  reset: () => void;
}

export const useConsoleStore = create<ConsoleState>((set) => ({
  stream: [],
  cards: [],
  energy: 100,
  hintsUsed: [],
  appendStream: (event) => set((s) => ({ stream: [...s.stream, event].slice(-400) })),
  appendCard: (card) => set((s) => ({ cards: [card, ...s.cards].slice(0, 50) })),
  setEnergy: (energy) => set({ energy }),
  useHint: (level) => set((s) => ({ hintsUsed: [...s.hintsUsed, level] })),
  reset: () => set({ stream: [], cards: [], energy: 100, hintsUsed: [] })
}));