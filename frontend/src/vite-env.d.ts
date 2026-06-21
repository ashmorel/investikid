/// <reference types="vite/client" />

// Build-time globals injected by vite.config `define` from the process
// environment (so Vercel/CI VITE_* vars reach the bundle — Vite's own
// import.meta.env only reads .env files). Empty string when unset.
declare const __API_BASE__: string;
declare const __WEB_ORIGIN__: string;
