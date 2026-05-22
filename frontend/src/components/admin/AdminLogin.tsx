import { useState } from 'react';
import { setAdminToken } from '@/lib/adminAuth';

interface AdminLoginProps {
  onAuthenticated: () => void;
}

export default function AdminLogin({ onAuthenticated }: AdminLoginProps) {
  const [token, setToken] = useState('');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token.trim()) return;
    setAdminToken(token.trim());
    onAuthenticated();
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-lg border border-slate-700 bg-slate-900 p-8">
        <h1 className="mb-6 text-xl font-bold text-slate-50">📚 Invest-Ed Admin</h1>
        <label htmlFor="admin-token" className="mb-2 block text-sm text-slate-400">
          Admin Token
        </label>
        <input
          id="admin-token"
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="mb-4 w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-slate-50 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
          placeholder="Enter admin token"
          autoComplete="off"
        />
        <button
          type="submit"
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-900"
        >
          Sign In
        </button>
      </form>
    </div>
  );
}
