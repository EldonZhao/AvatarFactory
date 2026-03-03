import type { PersonaStats } from '../types';
import { getContentByPersona, getReviewsForPersona } from './content';

export function getPersonaStats(id: string): PersonaStats {
  const contents = getContentByPersona(id);
  const reviews = getReviewsForPersona(id);

  const published = contents.filter(c => c.status === 'published');
  const drafts = contents.filter(c => c.status === 'draft');

  const contentByPillar: Record<string, number> = {};
  const contentByPlatform: Record<string, number> = {};

  let totalConsistency = 0;
  let totalPlatformFit = 0;
  let totalCompliance = 0;
  let totalEngagement = 0;
  let reviewCount = 0;

  for (const content of contents) {
    contentByPillar[content.pillar] = (contentByPillar[content.pillar] || 0) + 1;
    contentByPlatform[content.platform] = (contentByPlatform[content.platform] || 0) + 1;
  }

  for (const review of reviews) {
    totalConsistency += review.persona_consistency.score;
    totalPlatformFit += review.platform_fit.score;
    totalCompliance += review.compliance.score;
    totalEngagement += review.engagement_potential.score;
    reviewCount++;
  }

  const avgScore = reviewCount > 0
    ? (totalConsistency + totalPlatformFit + totalCompliance + totalEngagement) / (reviewCount * 4)
    : 0;

  return {
    persona_id: id,
    total_content: contents.length,
    published_content: published.length,
    draft_content: drafts.length,
    avg_review_score: Math.round(avgScore),
    content_by_pillar: contentByPillar,
    content_by_platform: contentByPlatform,
    score_distribution: {
      persona_consistency: reviewCount > 0 ? Math.round(totalConsistency / reviewCount) : 0,
      platform_fit: reviewCount > 0 ? Math.round(totalPlatformFit / reviewCount) : 0,
      compliance: reviewCount > 0 ? Math.round(totalCompliance / reviewCount) : 0,
      engagement_potential: reviewCount > 0 ? Math.round(totalEngagement / reviewCount) : 0
    }
  };
}
