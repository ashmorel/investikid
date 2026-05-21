import { useContext } from 'react';
import { AnnounceContext } from './announce-context';

export function useAnnounce() {
  return useContext(AnnounceContext);
}
