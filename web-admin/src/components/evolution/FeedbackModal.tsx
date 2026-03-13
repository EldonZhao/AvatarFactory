'use client';

import * as React from 'react';
import { useState } from 'react';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  personaId: string;
  onSuggestionsGenerated?: () => void;
}

export function FeedbackModal({ isOpen, onClose, personaId, onSuggestionsGenerated }: FeedbackModalProps) {
  const [feedback, setFeedback] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleSubmit = async () => {
    if (!feedback.trim()) return;

    setIsLoading(true);
    setResult(null);

    try {
      const response = await fetch(`/api/admin/personas/${personaId}/evolution/suggest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: feedback.trim() }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult({
          success: true,
          message: `成功生成 ${data.suggestions_count || 0} 条演进建议`,
        });
        setFeedback('');
        onSuggestionsGenerated?.();
      } else {
        setResult({
          success: false,
          message: data.detail || '生成建议失败',
        });
      }
    } catch (e) {
      setResult({
        success: false,
        message: '请求失败: ' + e,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setFeedback('');
    setResult(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg mx-4 rounded-xl bg-[hsl(var(--card))] border border-[hsl(var(--border))] shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[hsl(var(--border))]">
          <h2 className="text-lg font-semibold">提交反馈</h2>
          <button
            onClick={handleClose}
            className="p-1 rounded-lg hover:bg-[hsl(var(--accent))] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-4 space-y-4">
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            输入您对 Persona 的反馈或改进建议，系统将基于反馈生成演进建议。
          </p>

          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="例如：希望内容更加专业、减少表情符号使用、增加技术深度..."
            className="w-full h-32 p-3 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            disabled={isLoading}
          />

          {result && (
            <div
              className={`p-3 rounded-lg text-sm ${
                result.success
                  ? 'bg-green-500/10 text-green-600 border border-green-500/20'
                  : 'bg-red-500/10 text-red-600 border border-red-500/20'
              }`}
            >
              {result.message}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-[hsl(var(--border))]">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm rounded-lg bg-[hsl(var(--secondary))] text-[hsl(var(--secondary-foreground))] hover:opacity-90 transition-opacity"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !feedback.trim()}
            className="px-4 py-2 text-sm rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {isLoading ? '生成中...' : '生成建议'}
          </button>
        </div>
      </div>
    </div>
  );
}
