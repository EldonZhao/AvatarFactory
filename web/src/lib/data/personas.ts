import * as fs from 'node:fs';
import * as path from 'node:path';
import yaml from 'js-yaml';
import type { Persona, PersonaVersion } from '../types';

const KNOWLEDGE_BASE_PATH = process.env.KNOWLEDGE_BASE_PATH || path.resolve(process.cwd(), '../knowledges');

function getPersonasDir(): string {
  return path.join(KNOWLEDGE_BASE_PATH, 'personas');
}

export function getAllPersonaIds(): string[] {
  const personasDir = getPersonasDir();
  if (!fs.existsSync(personasDir)) {
    return [];
  }
  return fs.readdirSync(personasDir).filter(dir => {
    const configPath = path.join(personasDir, dir, 'config.yaml');
    return fs.existsSync(configPath);
  });
}

export function getPersona(id: string): Persona | null {
  const configPath = path.join(getPersonasDir(), id, 'config.yaml');
  if (!fs.existsSync(configPath)) {
    return null;
  }
  try {
    const content = fs.readFileSync(configPath, 'utf-8');
    return yaml.load(content) as Persona;
  } catch {
    return null;
  }
}

export function getAllPersonas(): Persona[] {
  const ids = getAllPersonaIds();
  return ids.map(id => getPersona(id)).filter((p): p is Persona => p !== null);
}

export function getPersonaHistory(id: string): PersonaVersion[] {
  const historyPath = path.join(getPersonasDir(), id, 'history.json');
  if (!fs.existsSync(historyPath)) {
    return [];
  }
  try {
    const content = fs.readFileSync(historyPath, 'utf-8');
    return JSON.parse(content) as PersonaVersion[];
  } catch {
    return [];
  }
}

export function getPersonaVersions(id: string): string[] {
  const versionsDir = path.join(getPersonasDir(), id, 'versions');
  if (!fs.existsSync(versionsDir)) {
    return [];
  }
  return fs.readdirSync(versionsDir)
    .filter(f => f.endsWith('.yaml'))
    .map(f => f.replace('.yaml', ''))
    .sort();
}

export function getPersonaVersion(id: string, version: string): Persona | null {
  const versionPath = path.join(getPersonasDir(), id, 'versions', `${version}.yaml`);
  if (!fs.existsSync(versionPath)) {
    return null;
  }
  try {
    const content = fs.readFileSync(versionPath, 'utf-8');
    return yaml.load(content) as Persona;
  } catch {
    return null;
  }
}

// getPersonaStats is in stats.ts to avoid circular dependency
