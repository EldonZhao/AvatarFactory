import * as fs from 'node:fs';
import * as path from 'node:path';
import type { Content, ReviewReport } from '../types';

const KNOWLEDGE_BASE_PATH = process.env.KNOWLEDGE_BASE_PATH || path.resolve(process.cwd(), '../knowledges');

function getPersonasDir(): string {
  return path.join(KNOWLEDGE_BASE_PATH, 'personas');
}

function parseContentFile(filePath: string, status: 'draft' | 'published'): Content | null {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(content);
    return { ...data, status };
  } catch {
    return null;
  }
}

export function getContentByPersona(personaId: string): Content[] {
  const personaDir = path.join(getPersonasDir(), personaId, 'content');
  const contents: Content[] = [];

  // Get drafts
  const draftsDir = path.join(personaDir, 'drafts');
  if (fs.existsSync(draftsDir)) {
    const draftFiles = fs.readdirSync(draftsDir).filter(f => f.endsWith('.json'));
    for (const file of draftFiles) {
      const content = parseContentFile(path.join(draftsDir, file), 'draft');
      if (content) {
        // Check if this draft was published
        const publishedDir = path.join(personaDir, 'published');
        const isPublished = fs.existsSync(publishedDir) &&
          fs.readdirSync(publishedDir).some(f => f.includes(content.id));
        if (!isPublished) {
          contents.push(content);
        }
      }
    }
  }

  // Get published
  const publishedDir = path.join(personaDir, 'published');
  if (fs.existsSync(publishedDir)) {
    const publishedFiles = fs.readdirSync(publishedDir).filter(f => f.endsWith('.json'));
    for (const file of publishedFiles) {
      const content = parseContentFile(path.join(publishedDir, file), 'published');
      if (content) contents.push(content);
    }
  }

  // Sort by created_at descending
  return contents.sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
}

export function getAllContent(): Content[] {
  const personasDir = getPersonasDir();
  if (!fs.existsSync(personasDir)) return [];

  const personaIds = fs.readdirSync(personasDir);
  const allContent: Content[] = [];

  for (const personaId of personaIds) {
    const contents = getContentByPersona(personaId);
    allContent.push(...contents);
  }

  return allContent.sort((a, b) =>
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
}

export function getContent(contentId: string): Content | null {
  const personasDir = getPersonasDir();
  if (!fs.existsSync(personasDir)) return null;

  const personaIds = fs.readdirSync(personasDir);

  for (const personaId of personaIds) {
    const contents = getContentByPersona(personaId);
    const found = contents.find(c => c.id === contentId);
    if (found) return found;
  }

  return null;
}

export function getReview(contentId: string): ReviewReport | null {
  const personasDir = getPersonasDir();
  if (!fs.existsSync(personasDir)) return null;

  const personaIds = fs.readdirSync(personasDir);

  for (const personaId of personaIds) {
    const reviewPath = path.join(personasDir, personaId, 'reviews', `${contentId}.json`);
    if (fs.existsSync(reviewPath)) {
      try {
        const content = fs.readFileSync(reviewPath, 'utf-8');
        return JSON.parse(content) as ReviewReport;
      } catch {
        return null;
      }
    }
  }

  return null;
}

export function getReviewsForPersona(personaId: string): ReviewReport[] {
  const reviewsDir = path.join(getPersonasDir(), personaId, 'reviews');
  if (!fs.existsSync(reviewsDir)) return [];

  const reviews: ReviewReport[] = [];
  const files = fs.readdirSync(reviewsDir).filter(f => f.endsWith('.json'));

  for (const file of files) {
    try {
      const content = fs.readFileSync(path.join(reviewsDir, file), 'utf-8');
      reviews.push(JSON.parse(content) as ReviewReport);
    } catch {
      // Skip invalid files
    }
  }

  return reviews.sort((a, b) =>
    new Date(b.reviewed_at).getTime() - new Date(a.reviewed_at).getTime()
  );
}

export function getRecentContent(limit: number = 10): Content[] {
  return getAllContent().slice(0, limit);
}
