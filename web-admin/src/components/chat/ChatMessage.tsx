import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: Record<string, any>;
  timestamp: Date;
}

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const [showMetadata, setShowMetadata] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
            : 'bg-[hsl(var(--card))] border border-[hsl(var(--border))] text-[hsl(var(--foreground))]'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none break-words">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        <div className="flex items-center justify-between mt-2 pt-2 border-t border-current/10">
          <span className="text-xs opacity-60">
            {message.timestamp.toLocaleTimeString('zh-CN', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>

          {!isUser && message.metadata && Object.keys(message.metadata).length > 0 && (
            <button
              onClick={() => setShowMetadata(!showMetadata)}
              className="text-xs opacity-60 hover:opacity-100 transition-opacity"
            >
              {showMetadata ? '隐藏详情' : '查看详情'}
            </button>
          )}
        </div>

        {showMetadata && message.metadata && (
          <div className="mt-2 p-2 rounded-lg bg-[hsl(var(--muted))] text-xs font-mono overflow-x-auto">
            <pre className="whitespace-pre-wrap break-words">
              {JSON.stringify(message.metadata, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
