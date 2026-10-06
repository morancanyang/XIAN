import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/** 关卡地图存储：当前关卡、已通关集合、能量（技术方案 5 store/levelStore）。 */
export interface LevelState {
  currentLevel: string | null;
  completed: string[];
  badges: string[];
  points: number;
  setCurrentLevel: (code: string | null) => void;
  markCompleted: (code: string, points: number) => void;
  setBadges: (badges: string[]) => void;
  reset: () => void;
}

export const useLevelStore = create<LevelState>()(
  persist(
    (set) => ({
      currentLevel: null,
      completed: [],
      badges: [],
      points: 0,
      setCurrentLevel: (currentLevel) => set({ currentLevel }),
      markCompleted: (code, points) =>
        set((s) => ({
          completed: s.completed.includes(code) ? s.completed : [...s.completed, code],
          points: s.points + points
        })),
      setBadges: (badges) => set({ badges }),
      reset: () => set({ currentLevel: null, completed: [], badges: [], points: 0 })
    }),
    { name: 'xian.level-store' }
  )
);