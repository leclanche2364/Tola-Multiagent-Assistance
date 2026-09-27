import { BlackboardRepository, type ProjectRow } from "../../../blackboard-tools/src/repository/blackboard.ts";
import { BlackboardError } from "../../../blackboard-tools/src/adapters/supabase.ts";
import { validateGetProject } from "../validate.ts";
import { redactError } from "../redact.ts";

export async function listProjects(
  db: BlackboardRepository
): Promise<ProjectRow[]> {
  try {
    return await db.listProjects();
  } catch (err) {
    throw new BlackboardError(
      "UNAVAILABLE",
      `failed to list projects: ${(err as Error).message}`,
      redactError(err).detail
    );
  }
}

export async function getProject(
  db: BlackboardRepository,
  projectId: string
): Promise<ProjectRow> {
  validateGetProject(projectId);
  try {
    return await db.getProject(projectId);
  } catch (err) {
    throw new BlackboardError(
      "NOT_FOUND",
      `project ${projectId} not found`,
      redactError(err).detail
    );
  }
}