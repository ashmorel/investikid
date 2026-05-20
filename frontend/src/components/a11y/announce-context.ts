import { createContext } from 'react';

export const AnnounceContext = createContext<(msg: string) => void>(() => {});
