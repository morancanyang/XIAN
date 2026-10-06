import { QueryClient } from '@tanstack/react-query';

/** TanStack Query 全局配置：错误不抛到全局，交由页面 ErrorState 呈现。 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      gcTime: 5 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false
    },
    mutations: { retry: 0 }
  }
});