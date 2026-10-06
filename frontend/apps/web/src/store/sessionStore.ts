import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Role } from '@xian/types';

/** 会话存储：登录态、租户上下文、当前 Agent / 战役 / 会话（技术方案 5 store/）。 */
export interface SessionState {
  token: string | null;
  userId: string | null;
  tenantId: string;
  role: Role;
  email: string;
  name: string;
  activeAgentId: string | null;
  activeCampaignId: string | null;
  activeSessionId: string | null;
  reducedMotion: boolean;
  setAuth: (payload: {
    token?: string | null;
    userId?: string | null;
    tenantId?: string;
    role?: Role;
    email?: string;
    name?: string;
  }) => void;
  logout: () => void;
  setActiveAgent: (id: string | null) => void;
  setActiveCampaign: (id: string | null) => void;
  setActiveSession: (id: string | null) => void;
  setReducedMotion: (value: boolean) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      tenantId: '00000000-0000-0000-0000-000000000001',
      role: 'admin',
      email: 'demo@xian.local',
      name: '演示管理员',
      activeAgentId: null,
      activeCampaignId: null,
      activeSessionId: null,
      reducedMotion: false,
      setAuth: (payload) => set((s) => ({ ...s, ...payload })),
      logout: () =>
        set({
          token: null,
          userId: null,
          activeAgentId: null,
          activeCampaignId: null,
          activeSessionId: null
        }),
      setActiveAgent: (id) => set({ activeAgentId: id }),
      setActiveCampaign: (id) => set({ activeCampaignId: id }),
      setActiveSession: (id) => set({ activeSessionId: id }),
      setReducedMotion: (value) => set({ reducedMotion: value })
    }),
    { name: 'xian.session-store' }
  )
);