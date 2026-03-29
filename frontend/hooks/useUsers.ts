import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import type { User } from '@/lib/types';

export function useUsers(role?: string) {
  return useQuery<User[]>({
    queryKey: ['users', role],
    queryFn: async () => {
      const res = await api.get('/api/v1/users', { params: role ? { role } : undefined });
      return res.data;
    },
  });
}
