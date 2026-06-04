import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { simulatorApi, type ChartCoachResponse } from '@/api/simulator';
import { Button } from '@/components/ui/button';

type Message = { role: 'user' | 'assistant'; content: string };

type Props = {
  ticker: string;
  exchange: string;
  period: string;
  onClose: () => void;
};

export function ChartCoachPanel({ ticker, exchange, period, onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [remaining, setRemaining] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useMutation<ChartCoachResponse | null, Error, string>({
    mutationFn: (msg) =>
      simulatorApi.sendChartCoachMessage({
        ticker,
        exchange,
        period,
        message: msg,
        conversation_id: conversationId ?? null,
      }),
    onSuccess: (data) => {
      if (!data) return;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response },
      ]);
      setConversationId(data.conversation_id);
      setRemaining(data.messages_remaining);
    },
  });

  const handleSend = () => {
    const msg = input.trim();
    if (!msg || sendMessage.isPending) return;
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    setInput('');
    sendMessage.mutate(msg);
  };

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 mx-auto max-w-2xl animate-in slide-in-from-bottom">
      <div className="rounded-t-2xl border-2 border-brand-200 bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-brand-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">💡</span>
            <span className="font-bold text-gray-900">Coach Penny</span>
            <span className="rounded-full bg-purple-100 px-2 py-0.5 text-xs text-purple-700">{ticker} Chart</span>
          </div>
          <div className="flex items-center gap-3">
            {remaining !== null && (
              <span className="text-xs text-gray-400">{remaining} messages left</span>
            )}
            <button onClick={onClose} className="text-lg text-gray-400 hover:text-gray-600">✕</button>
          </div>
        </div>

        <div className="max-h-64 space-y-3 overflow-y-auto p-4">
          {messages.length === 0 && (
            <p className="text-center text-sm text-gray-400">
              Ask me anything about this {ticker} chart! 📊
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-brand-gradient text-white'
                    : 'bg-brand-50 text-gray-800'
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}
          {sendMessage.isPending && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-brand-50 px-3 py-2 text-sm text-gray-400">
                Thinking…
              </div>
            </div>
          )}
          {sendMessage.isError && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-xl bg-danger-50 px-3 py-2 text-sm text-danger-600">
                Something went wrong. Try sending your message again.
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="flex gap-2 border-t border-brand-100 p-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about the chart…"
            maxLength={200}
            className="flex-1 rounded-xl border border-brand-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-300"
            disabled={remaining === 0}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || sendMessage.isPending || remaining === 0}
            className="rounded-xl bg-brand-gradient px-4 text-white"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
