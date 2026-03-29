import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      full_name: string;
      email: string;
      password: string;
      role: string;
      timezone?: string;
    }) => {
      const res = await api.post('/api/v1/users', data);
      return res.data as User;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });
}

export function useUpdateUser(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: Partial<Pick<User, 'role' | 'timezone' | 'is_active'>>) => {
      const res = await api.patch(`/api/v1/users/${id}`, data);
      return res.data as User;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/api/v1/users/${id}`);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users'] }),
  });
}
