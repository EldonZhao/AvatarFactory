import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Get base URL for links - works in both Astro and client-side React
export function getBaseUrl(): string {
  // In browser, check if we're on /admin path
  if (typeof window !== 'undefined') {
    const path = window.location.pathname;
    if (path.startsWith('/admin')) {
      return '/admin';
    }
  }
  // Default (local dev)
  return '';
}

// Helper to build URLs with base path
export function buildUrl(path: string): string {
  const base = getBaseUrl();
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date, format: 'full' | 'short' | 'relative' = 'short'): string {
  const d = new Date(date);

  if (format === 'relative') {
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins} 分钟前`;
    if (diffHours < 24) return `${diffHours} 小时前`;
    if (diffDays < 7) return `${diffDays} 天前`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} 周前`;
    return d.toLocaleDateString('zh-CN');
  }

  if (format === 'full') {
    return d.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  return d.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric'
  });
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}

export function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-500';
  if (score >= 75) return 'text-blue-500';
  if (score >= 60) return 'text-yellow-500';
  return 'text-red-500';
}

export function getScoreBgColor(score: number): string {
  if (score >= 90) return 'bg-green-500/10 border-green-500/20';
  if (score >= 75) return 'bg-blue-500/10 border-blue-500/20';
  if (score >= 60) return 'bg-yellow-500/10 border-yellow-500/20';
  return 'bg-red-500/10 border-red-500/20';
}

export function getPlatformColor(platform: string): string {
  const colors: Record<string, string> = {
    xiaohongshu: 'bg-red-500',
    bluesky: 'bg-blue-500',
    twitter: 'bg-sky-500',
    wecom: 'bg-green-500'
  };
  return colors[platform] || 'bg-gray-500';
}

export function getPlatformName(platform: string): string {
  const names: Record<string, string> = {
    xiaohongshu: '小红书',
    bluesky: 'Bluesky',
    twitter: 'Twitter',
    wecom: '企业微信'
  };
  return names[platform] || platform;
}
