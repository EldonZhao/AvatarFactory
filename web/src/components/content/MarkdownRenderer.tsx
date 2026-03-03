'use client';

import * as React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn('prose prose-sm dark:prose-invert max-w-none', className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold mt-6 mb-4 text-[hsl(var(--foreground))]">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-bold mt-5 mb-3 text-[hsl(var(--foreground))]">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-semibold mt-4 mb-2 text-[hsl(var(--foreground))]">{children}</h3>
          ),
          p: ({ children }) => (
            <p className="my-3 text-[hsl(var(--foreground))] leading-relaxed">{children}</p>
          ),
          ul: ({ children }) => (
            <ul className="my-3 ml-4 list-disc space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="my-3 ml-4 list-decimal space-y-1">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-[hsl(var(--foreground))]">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-4 pl-4 border-l-4 border-[hsl(var(--primary))] italic text-[hsl(var(--muted-foreground))]">
              {children}
            </blockquote>
          ),
          code: ({ children, className }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code className="px-1.5 py-0.5 rounded bg-[hsl(var(--muted))] text-[hsl(var(--foreground))] text-sm font-mono">
                  {children}
                </code>
              );
            }
            return (
              <code className="block p-4 rounded-lg bg-[hsl(var(--muted))] text-[hsl(var(--foreground))] text-sm font-mono overflow-x-auto">
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="my-4 p-4 rounded-lg bg-[hsl(var(--muted))] overflow-x-auto">
              {children}
            </pre>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[hsl(var(--primary))] hover:underline"
            >
              {children}
            </a>
          ),
          hr: () => (
            <hr className="my-6 border-[hsl(var(--border))]" />
          ),
          strong: ({ children }) => (
            <strong className="font-bold text-[hsl(var(--foreground))]">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic">{children}</em>
          ),
          table: ({ children }) => (
            <div className="my-4 overflow-x-auto">
              <table className="min-w-full border-collapse border border-[hsl(var(--border))]">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="px-4 py-2 bg-[hsl(var(--muted))] border border-[hsl(var(--border))] font-semibold text-left">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2 border border-[hsl(var(--border))]">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
