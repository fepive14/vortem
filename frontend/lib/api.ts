import axios from 'axios';

export const api = axios.create({
  baseURL: '',
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      typeof window !== 'undefined' &&
      window.location.pathname !== '/login'
    ) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
