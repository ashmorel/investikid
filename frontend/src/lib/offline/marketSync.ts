// frontend/src/lib/offline/marketSync.ts
import { getOfflineBundle } from '@/api/content';
import type { CacheScope } from './scope';
import {
  getLastSync,
  setLastSync,
  reconcileIds,
  upsertModules,
  upsertModuleLevels,
  upsertLevelLessons,
  upsertLesson,
} from './contentStore';
import { isOfflineDbAvailable } from './sqlite';

/**
 * Fetch the offline bundle from the server and write it into the SQLite store.
 * Best-effort: swallows all errors, leaving the cache and last_sync cursor untouched.
 * No-op on web (when SQLite is unavailable).
 */
export async function syncMarket(scope: CacheScope): Promise<void> {
  if (!isOfflineDbAvailable()) return;

  try {
    const since = await getLastSync(scope);
    const bundle = await getOfflineBundle(since);
    if (!bundle) return;

    await upsertModules(scope, bundle.modules);

    for (const [moduleId, levels] of Object.entries(bundle.module_levels)) {
      await upsertModuleLevels(scope, moduleId, levels);
    }

    for (const [levelId, lessons] of Object.entries(bundle.level_lessons)) {
      await upsertLevelLessons(scope, levelId, lessons);
    }

    // Build lessonId → levelId map from level_lessons so we can pass level context
    // to each upserted lesson (LessonOut has module_id but no level_id).
    const lessonLevelMap = new Map<string, string>();
    for (const [levelId, summaries] of Object.entries(bundle.level_lessons)) {
      for (const summary of summaries) {
        lessonLevelMap.set(summary.id, levelId);
      }
    }

    for (const lesson of bundle.lessons) {
      await upsertLesson(scope, lesson, lessonLevelMap.get(lesson.id) ?? null);
    }

    await reconcileIds(scope, bundle.current_ids);
    await setLastSync(scope, bundle.server_time);
  } catch {
    /* best-effort: swallow — leave cache + last_sync untouched */
  }
}
