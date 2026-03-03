'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import type { Persona } from '@/lib/types';

interface PersonaInfoProps {
  persona: Persona;
}

export function PersonaInfo({ persona }: PersonaInfoProps) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Identity */}
      <Card>
        <CardHeader>
          <CardTitle>身份定义</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))]">名称</label>
            <p className="font-medium">{persona.identity.name}</p>
          </div>
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))]">标语</label>
            <p className="font-medium">{persona.identity.tagline}</p>
          </div>
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))] block mb-2">专长领域</label>
            <div className="flex flex-wrap gap-2">
              {persona.identity.expertise.map((exp) => (
                <Badge key={exp} variant="secondary">{exp}</Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Voice Style */}
      <Card>
        <CardHeader>
          <CardTitle>表达风格</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))]">语气</label>
            <p className="font-medium">{persona.voice_style.tone}</p>
          </div>
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))]">Emoji 使用</label>
            <p className="font-medium">{persona.voice_style.emoji_usage}</p>
          </div>
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))] block mb-2">语言模式</label>
            <ul className="space-y-1">
              {persona.voice_style.language_patterns.map((pattern, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-[hsl(var(--primary))] mt-1">•</span>
                  <span>{pattern}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Target Audience */}
      <Card>
        <CardHeader>
          <CardTitle>目标受众</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))]">主要受众</label>
            <p className="font-medium">{persona.target_audience.primary}</p>
          </div>
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))] block mb-2">痛点</label>
            <ul className="space-y-1">
              {persona.target_audience.pain_points.map((point, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-red-500 mt-1">•</span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))] block mb-2">目标</label>
            <ul className="space-y-1">
              {persona.target_audience.goals.map((goal, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-green-500 mt-1">•</span>
                  <span>{goal}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Boundaries */}
      <Card>
        <CardHeader>
          <CardTitle>边界规则</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))] block mb-2">避免</label>
            <ul className="space-y-1">
              {persona.boundaries.avoid.map((item, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-red-500">✗</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <label className="text-sm text-[hsl(var(--muted-foreground))] block mb-2">合规要求</label>
            <ul className="space-y-1">
              {persona.boundaries.compliance.map((item, i) => (
                <li key={i} className="text-sm flex items-start gap-2">
                  <span className="text-green-500">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
