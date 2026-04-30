import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '@/api/client';

export function useChildAuthGuard(error: unknown) {
  const navigate = useNavigate();
  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) {
      navigate('/login', { replace: true });
    }
  }, [error, navigate]);
}
