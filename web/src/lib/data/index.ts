/**
 * Data layer - re-exports API client functions for SSR
 *
 * All data is now fetched from the FastAPI backend via API calls.
 * This enables server-side rendering without direct file system access.
 */

export {
  // Persona functions
  getAllPersonas,
  getAllPersonaIds,
  getPersona,
  getPersonaHistory,
  getPersonaVersions,
  getPersonaStats,

  // Content functions
  getAllContent,
  getAllContentIds,
  getRecentContent,
  getContent,
  getContentByPersona,
  getReview,
  getReviewsForPersona,

  // Scheduler functions
  getAllTasks,
  getTask,
  getTasksByPersona,
  getActiveTasks,
  getTaskStats,

  // Timeline & Stats functions
  getTimelineEvents,
  getGlobalStats,

  // Dashboard (optimized)
  getDashboardData,
} from '../api/client';

export type { DashboardData } from '../api/client';

// Note: getPersonaVersion is not implemented in the API yet
// If needed, it can be added to the chronicle_routes.py
