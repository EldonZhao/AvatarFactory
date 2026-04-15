'use client';

import * as React from 'react';
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Use relative URLs to ensure cookies are sent correctly (same origin)
const API_BASE_URL = '';

interface SchedulerTask {
  id: string;
  name: string;
  task_type: string;
  schedule: string;
  platform?: string;
  enabled: boolean;
  persona_id?: string;
  last_run?: string;
  last_status?: string;
  run_count?: number;
}

interface TaskActionsProps {
  task: SchedulerTask;
  onUpdated?: () => void;
}

export function TaskActions({ task, onUpdated }: TaskActionsProps) {
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Default refresh handler - reload the page if no callback provided
  const handleRefresh = () => {
    if (typeof onUpdated === 'function') {
      onUpdated();
    } else {
      window.location.reload();
    }
  };

  const handleToggle = async () => {
    try {
      setLoading('toggle');
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/admin/scheduler/tasks/${task.id}/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to toggle task');
      }
      handleRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Toggle failed');
    } finally {
      setLoading(null);
    }
  };

  const handleRun = async () => {
    try {
      setLoading('run');
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/admin/scheduler/tasks/${task.id}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to run task');
      }
      handleRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Run failed');
    } finally {
      setLoading(null);
    }
  };

  const handleDelete = async () => {
    try {
      setLoading('delete');
      setError(null);
      const response = await fetch(`${API_BASE_URL}/api/admin/scheduler/tasks/${task.id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!response.ok) {
        throw new Error('Failed to delete task');
      }
      setShowDeleteConfirm(false);
      handleRefresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    } finally {
      setLoading(null);
    }
  };

  return (
    <>
      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        {/* Toggle Button */}
        <button
          onClick={handleToggle}
          disabled={loading === 'toggle'}
          className={`p-2 rounded-lg transition-colors ${
            task.enabled
              ? 'text-green-600 hover:bg-green-500/10'
              : 'text-gray-400 hover:bg-gray-500/10'
          } disabled:opacity-50`}
          title={task.enabled ? '禁用任务' : '启用任务'}
        >
          {loading === 'toggle' ? (
            <LoadingSpinner />
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d={task.enabled
                  ? "M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  : "M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                }
              />
              {!task.enabled && (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              )}
            </svg>
          )}
        </button>

        {/* Run Now Button */}
        <button
          onClick={handleRun}
          disabled={loading === 'run'}
          className="p-2 rounded-lg text-blue-600 hover:bg-blue-500/10 transition-colors disabled:opacity-50"
          title="立即运行"
        >
          {loading === 'run' ? (
            <LoadingSpinner />
          ) : (
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          )}
        </button>

        {/* Edit Button */}
        <button
          onClick={() => setShowEditModal(true)}
          className="p-2 rounded-lg text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--accent))] transition-colors"
          title="编辑任务"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>

        {/* Delete Button */}
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="p-2 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors"
          title="删除任务"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mt-2 text-xs text-red-500">{error}</div>
      )}

      {/* Edit Modal */}
      <AnimatePresence>
        {showEditModal && (
          <TaskEditModal
            task={task}
            onClose={() => setShowEditModal(false)}
            onSaved={() => {
              setShowEditModal(false);
              handleRefresh();
            }}
          />
        )}
      </AnimatePresence>

      {/* Delete Confirmation */}
      <AnimatePresence>
        {showDeleteConfirm && (
          <DeleteConfirmModal
            taskName={task.name}
            loading={loading === 'delete'}
            onConfirm={handleDelete}
            onCancel={() => setShowDeleteConfirm(false)}
          />
        )}
      </AnimatePresence>
    </>
  );
}

// Loading Spinner Component
function LoadingSpinner() {
  return (
    <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}

// Task Edit Modal Component
interface TaskEditModalProps {
  task: SchedulerTask;
  onClose: () => void;
  onSaved: () => void;
}

function TaskEditModal({ task, onClose, onSaved }: TaskEditModalProps) {
  const [name, setName] = useState(task.name);
  const [schedule, setSchedule] = useState(task.schedule);
  const [platform, setPlatform] = useState(task.platform || '');
  const [enabled, setEnabled] = useState(task.enabled);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/admin/scheduler/tasks/${task.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          name,
          schedule,
          platform: platform || undefined,
          enabled,
        }),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || 'Failed to update task');
      }

      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Update failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative w-full max-w-lg mx-4 bg-[hsl(var(--card))] rounded-xl shadow-xl border border-[hsl(var(--border))] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[hsl(var(--border))]">
          <div>
            <h2 className="text-lg font-semibold">编辑任务</h2>
            <p className="text-sm text-[hsl(var(--muted-foreground))]">
              修改任务配置
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-[hsl(var(--accent))] transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Task Name */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium">任务名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            />
          </div>

          {/* Schedule */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium">Cron 表达式</label>
            <input
              type="text"
              value={schedule}
              onChange={(e) => setSchedule(e.target.value)}
              placeholder="0 9 * * *"
              className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            />
            <p className="text-xs text-[hsl(var(--muted-foreground))]">
              格式: 分 时 日 月 周。例如: 0 9 * * * = 每天早上 9 点
            </p>
          </div>

          {/* Platform */}
          <div className="space-y-1.5">
            <label className="block text-sm font-medium">目标平台</label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
            >
              <option value="">不指定</option>
              <option value="bluesky">Bluesky</option>
              <option value="xiaohongshu">小红书</option>
              <option value="twitter">Twitter</option>
              <option value="linkedin">LinkedIn</option>
              <option value="threads">Threads</option>
            </select>
          </div>

          {/* Enabled Toggle */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">启用状态</label>
            <button
              type="button"
              onClick={() => setEnabled(!enabled)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                enabled ? 'bg-green-500' : 'bg-gray-300'
              }`}
            >
              <span
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                  enabled ? 'left-7' : 'left-1'
                }`}
              />
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 text-red-600 border border-red-500/20 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[hsl(var(--border))] flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm rounded-lg hover:bg-[hsl(var(--accent))] transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
          >
            {saving && <LoadingSpinner />}
            保存
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// Delete Confirmation Modal
interface DeleteConfirmModalProps {
  taskName: string;
  loading: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

function DeleteConfirmModal({ taskName, loading, onConfirm, onCancel }: DeleteConfirmModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onCancel}
      />

      {/* Modal */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative w-full max-w-md mx-4 bg-[hsl(var(--card))] rounded-xl shadow-xl border border-[hsl(var(--border))] p-6"
      >
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
            <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold">删除任务</h3>
            <p className="text-sm text-[hsl(var(--muted-foreground))] mt-1">
              确定要删除任务 <strong>"{taskName}"</strong> 吗？此操作无法撤销。
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-lg hover:bg-[hsl(var(--accent))] transition-colors disabled:opacity-50"
          >
            取消
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {loading && <LoadingSpinner />}
            删除
          </button>
        </div>
      </motion.div>
    </div>
  );
}

export default TaskActions;
