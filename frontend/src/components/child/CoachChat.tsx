import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { aiApi, type CoachAction, type CoachChatResponse } from '@/api/ai';
import { useCoachGreeting } from '@/hooks/useCoachGreeting';
import { Button } from '@/components/ui/button';
import { Penny } from '@/components/child/ui/Penny';

type Message = {
  role: 'user' | 'assistant';
  content: string;
  actions?: CoachAction[];
};

type CoachChatProps = {
  onNavigate?: () => void;
  showHeader?: boolean;
};

const SUGGESTION_CHIPS = [
  'What should I learn next?',
  'Review my weak spots',
  'How am I doing?',
];

function actionToPath(action: CoachAction): string {
  if (action.type === 'lesson' && action.lesson_id) {
    return `/lessons/${action.module_id}/${action.lesson_id}`;
  }
  return `/lessons/${action.module_id}`;
}

export function CoachChat({ onNavigate, showHeader = true }: CoachChatProps) {
  const { greeting, isLoading: greetingLoading } = useCoachGreeting();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [remaining, setRemaining] = useState<number | null>(null);
  const [chipsSent, setChipsSent] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesEndRef.current?.scrollIntoView) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const sendMessage = useMutation<CoachChatResponse | null, Error, string>({
    mutationFn: (msg) => aiApi.sendCoachMessage(msg, conversationId),
    onSuccess: (data) => {
      if (!data) return;
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response, actions: data.actions },
      ]);
      setConversationId(data.conversation_id);
      setRemaining(data.messages_remaining);
    },
  });

  const handleSend = (text?: string) => {
    const msg = (text ?? input).trim();
    if (!msg || sendMessage.isPending) return;
    setMessages((prev) => [...prev, { role: 'user', content: msg }]);
    if (!text) setInput('');
    setChipsSent(true);
    sendMessage.mutate(msg);
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      {showHeader && (
        <div className="mb-4 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100" aria-hidden="true">
              <Penny size={28} mood="happy" />
            </span>
            <span className="font-bold text-gray-900">Coach Penny</span>
          </div>
          {remaining !== null && (
            <span className="ml-auto text-xs text-gray-400">{remaining} messages left</span>
          )}
        </div>
      )}

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto">
        {!greetingLoading && greeting && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl bg-brand-50 px-3 py-2 text-sm text-gray-800">
              {greeting}
            </div>
          </div>
        )}

        {!chipsSent && (
          <div className="flex flex-wrap gap-2.5">
            {SUGGESTION_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="rounded-full border border-brand-300 bg-white px-3 py-1.5 text-xs font-medium text-brand-700 transition-colors hover:bg-brand-50"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i}>
            <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-brand-gradient text-white'
                    : 'bg-brand-50 text-gray-800'
                }`}
              >
                {m.content}
              </div>
            </div>
            {m.actions && m.actions.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-2 pl-1">
                {m.actions.map((a, j) => (
                  <Link
                    key={j}
                    to={actionToPath(a)}
                    onClick={() => onNavigate?.()}
                    className="inline-flex items-center rounded-full bg-brand-100 px-3 py-1 text-xs font-medium text-brand-800 transition-colors hover:bg-brand-200"
                  >
                    {a.label} →
                  </Link>
                ))}
              </div>
            )}
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
            <div className="max-w-[85%] rounded-xl bg-danger-50 px-3 py-2 text-sm text-danger-600">
              Something went wrong. Try sending your message again.
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="mt-4 flex gap-2 border-t border-brand-100 pt-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask Coach Penny…"
          maxLength={200}
          className="flex-1 rounded-xl border border-brand-200 px-3 py-2 text-base focus:outline-none focus:ring-2 focus:ring-brand-300"
          disabled={remaining === 0}
        />
        <Button
          onClick={() => handleSend()}
          disabled={!input.trim() || sendMessage.isPending || remaining === 0}
          className="rounded-xl bg-brand-gradient px-4 text-white"
        >
          Send
        </Button>
      </div>
    </div>
  );
}
