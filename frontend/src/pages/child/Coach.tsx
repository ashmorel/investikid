import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { aiApi, type CoachChatResponse, type CoachAction } from '@/api/ai';
import { useCoachGreeting } from '@/hooks/useCoachGreeting';
import { Button } from '@/components/ui/button';

type Message = {
  role: 'user' | 'assistant';
  content: string;
  actions?: CoachAction[];
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

export default function Coach() {
  const navigate = useNavigate();
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
    <div className="mx-auto flex max-w-2xl flex-col px-4 py-4">
      <div className="mb-4 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="text-gray-400 hover:text-gray-600"
          aria-label="Go back"
        >
          ←
        </button>
        <div className="flex items-center gap-2">
          <span className="text-xl">💡</span>
          <span className="font-bold text-gray-900">Coach Penny</span>
        </div>
        {remaining !== null && (
          <span className="ml-auto text-xs text-gray-400">{remaining} messages left</span>
        )}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto">
        {/* Template greeting */}
        {!greetingLoading && greeting && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-800">
              {greeting}
            </div>
          </div>
        )}

        {/* Suggestion chips */}
        {!chipsSent && (
          <div className="flex flex-wrap gap-2">
            {SUGGESTION_CHIPS.map((chip) => (
              <button
                key={chip}
                onClick={() => handleSend(chip)}
                className="rounded-full border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-50"
              >
                {chip}
              </button>
            ))}
          </div>
        )}

        {/* Message bubbles */}
        {messages.map((m, i) => (
          <div key={i}>
            <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                  m.role === 'user'
                    ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-white'
                    : 'bg-amber-50 text-gray-800'
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
                    className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800 transition-colors hover:bg-amber-200"
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
            <div className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-400">
              Thinking…
            </div>
          </div>
        )}

        {sendMessage.isError && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
              Something went wrong. Try sending your message again.
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="mt-4 flex gap-2 border-t border-amber-100 pt-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask Coach Penny…"
          maxLength={200}
          className="flex-1 rounded-xl border border-amber-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
          disabled={remaining === 0}
        />
        <Button
          onClick={() => handleSend()}
          disabled={!input.trim() || sendMessage.isPending || remaining === 0}
          className="rounded-xl bg-gradient-to-r from-amber-400 to-orange-500 px-4 text-white"
        >
          Send
        </Button>
      </div>
    </div>
  );
}
