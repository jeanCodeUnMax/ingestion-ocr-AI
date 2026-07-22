import type { CoverageRecord, DocumentManifest } from "../types.js";

export function computeCoverage(manifest: Pick<DocumentManifest, "pages" | "batches" | "totalPages">): CoverageRecord {
  const expectedIds = Array.from(
    { length: manifest.totalPages },
    (_, index) => `page_${String(index + 1).padStart(4, "0")}`
  );
  const actualIds = manifest.pages.map((page) => page.pageId);
  const actualSet = new Set(actualIds);
  const missingPageIds = expectedIds.filter((id) => !actualSet.has(id));

  const inventoryCounts = new Map<string, number>();
  for (const id of actualIds) inventoryCounts.set(id, (inventoryCounts.get(id) ?? 0) + 1);
  const duplicateInventoryIds = [...inventoryCounts.entries()]
    .filter(([, count]) => count > 1)
    .map(([id]) => id);

  const successful = manifest.pages.filter((page) =>
    page.status === "native_success" || page.status === "vision_success"
  ).length;
  const failed = manifest.pages.filter((page) => page.status === "failed").length;
  const pending = manifest.pages.length - successful - failed;

  const visionPages = manifest.pages.filter((page) => page.requiresVision);
  const leafBatches = manifest.batches.filter((batch) => batch.status !== "split");
  const assignments = leafBatches.flatMap((batch) => batch.pageIds);
  const counts = new Map<string, number>();
  for (const id of assignments) counts.set(id, (counts.get(id) ?? 0) + 1);

  const duplicateLeafAssignments = [...new Set([
    ...duplicateInventoryIds,
    ...[...counts.entries()]
      .filter(([, count]) => count > 1)
      .map(([id]) => id)
  ])].sort();

  const assignedVisionIds = new Set(assignments);
  const unassignedVision = visionPages
    .map((page) => page.pageId)
    .filter((id) => !assignedVisionIds.has(id));

  return {
    pagesDetected: manifest.totalPages,
    pagesSuccessful: successful,
    pagesFailed: failed,
    pagesPending: pending,
    visionPagesExpected: visionPages.length,
    visionPagesAssignedToLeafBatches: assignedVisionIds.size,
    missingPageIds: [...new Set([...missingPageIds, ...unassignedVision])].sort(),
    duplicateLeafAssignments,
    isComplete:
      manifest.pages.length === manifest.totalPages &&
      successful === manifest.totalPages &&
      failed === 0 &&
      pending === 0 &&
      missingPageIds.length === 0 &&
      unassignedVision.length === 0 &&
      duplicateLeafAssignments.length === 0
  };
}
