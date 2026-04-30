import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '@/api/client';

export function useParentAuthGuard(error: unknown) {
  const navigate = useNavigate();
  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) {
      navigate('/parent/login', { replace: true });
    }
  }, [error, navigate]);
}
