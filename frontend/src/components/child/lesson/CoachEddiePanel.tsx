import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { aiApi, type TutorResponse } from '@/api/ai';
import { Button } from '@/components/ui/button';

type Message = { role: 'user' | 'assistant'; content: string };

type Props = {
  lessonId: string;
  onClose: () => void;
};

export function CoachEddiePanel({ lessonId, onClose }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [remaining, setRemaining] = useState<number | null>(null);

  const sendMessage = useMutation<TutorResponse | null, Error, string>({
    mutationFn: (msg) => aiApi.sendTutorMessage(lessonId, msg, conversationId),
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
      <div className="rounded-t-2xl border-2 border-amber-200 bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-amber-100 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">💡</span>
            <span className="font-bold text-gray-900">Coach Eddie</span>
          </div>
          <div className="flex items-center gap-3">
            {remaining !== null && (
              <span className="text-xs text-gray-400">{remaining} messages left</span>
            )}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">✕</button>
          </div>
        </div>

        {/* Messages */}
        <div className="max-h-64 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <p className="text-sm text-gray-400 text-center">
              Ask me anything about this quest! 🎯
            </p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                m.role === 'user'
                  ? 'bg-gradient-to-r from-amber-400 to-orange-500 text-white'
                  : 'bg-amber-50 text-gray-800'
              }`}>
                {m.content}
              </div>
            </div>
          ))}
          {sendMessage.isPending && (
            <div className="flex justify-start">
              <div className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-gray-400">
                Thinking...
              </div>
            </div>
          )}
          {sendMessage.isError && (
            <div className="flex justify-start" role="alert">
              <div className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
                Coach Eddie couldn't answer just now. Please try again in a moment.
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-amber-100 p-3 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask Coach Eddie..."
            maxLength={200}
            className="flex-1 rounded-xl border border-amber-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-300"
            disabled={remaining === 0}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || sendMessage.isPending || remaining === 0}
            className="bg-gradient-to-r from-amber-400 to-orange-500 text-white rounded-xl px-4"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
