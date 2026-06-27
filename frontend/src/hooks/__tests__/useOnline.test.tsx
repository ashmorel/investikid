import { renderHook, act } from '@testing-library/react';
import { onlineManager } from '@tanstack/react-query';
import { useOnline } from '../useOnline';

it('reflects onlineManager transitions', () => {
  onlineManager.setOnline(true);
  const { result } = renderHook(() => useOnline());
  expect(result.current).toBe(true);
  act(() => onlineManager.setOnline(false));
  expect(result.current).toBe(false);
  act(() => onlineManager.setOnline(true));
  expect(result.current).toBe(true);
});
