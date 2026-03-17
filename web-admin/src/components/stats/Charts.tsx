'use client';

import * as React from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';

interface ContentTrendChartProps {
  data: { date: string; count: number }[];
}

export function ContentTrendChart({ data }: ContentTrendChartProps) {
  const chartData = data.map((d) => ({
    ...d,
    date: d.date.slice(5), // MM-DD format
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>内容创作趋势</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="contentGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(221.2, 83.2%, 53.3%)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(221.2, 83.2%, 53.3%)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <Area
                type="monotone"
                dataKey="count"
                stroke="hsl(221.2, 83.2%, 53.3%)"
                strokeWidth={2}
                fill="url(#contentGradient)"
                name="内容数"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

interface ScoreDistributionChartProps {
  data: {
    persona_consistency: number;
    platform_fit: number;
    compliance: number;
    engagement_potential: number;
  };
}

export function ScoreDistributionChart({ data }: ScoreDistributionChartProps) {
  const chartData = [
    { name: '人设一致性', value: data.persona_consistency, fill: '#3b82f6' },
    { name: '平台适配度', value: data.platform_fit, fill: '#22c55e' },
    { name: '合规性', value: data.compliance, fill: '#eab308' },
    { name: '互动潜力', value: data.engagement_potential, fill: '#a855f7' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>评分分布</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                type="number"
                domain={[0, 100]}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
              />
              <YAxis
                type="category"
                dataKey="name"
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                width={80}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

interface ContentByPillarChartProps {
  data: Record<string, number>;
}

export function ContentByPillarChart({ data }: ContentByPillarChartProps) {
  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));
  const COLORS = ['#3b82f6', '#22c55e', '#eab308', '#a855f7', '#ec4899', '#f97316'];

  return (
    <Card>
      <CardHeader>
        <CardTitle>内容支柱分布</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

interface ContentByPlatformChartProps {
  data: Record<string, number>;
}

export function ContentByPlatformChart({ data }: ContentByPlatformChartProps) {
  const platformNames: Record<string, string> = {
    xiaohongshu: '小红书',
    bluesky: 'Bluesky',
    twitter: 'Twitter',
    wecom: '企业微信',
  };

  const chartData = Object.entries(data).map(([key, value]) => ({
    name: platformNames[key] || key,
    value,
  }));

  const COLORS = ['#ef4444', '#3b82f6', '#06b6d4', '#22c55e'];

  return (
    <Card>
      <CardHeader>
        <CardTitle>平台分布</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--card))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                }}
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
