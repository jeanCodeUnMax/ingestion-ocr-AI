import { appendFile, mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";

export interface UsageEvent {
  at: string;
  tenantId: string;
  userId: string;
  documentId: string;
  metric: "document" | "page" | "ocr_page" | "analysis_chunk" | "embedding_chunk";
  quantity: number;
  metadata?: Record<string, unknown>;
}

export class BillingLedger {
  private filePath = path.join(config.billingRoot, "usage.jsonl");

  async record(event: UsageEvent): Promise<void> {
    if (!config.featureFlags.billing) return;
    await mkdir(config.billingRoot, { recursive: true });
    await appendFile(this.filePath, `${JSON.stringify(event)}\n`, "utf8");
  }

  async list(tenantId?: string): Promise<UsageEvent[]> {
    try {
      const lines = (await readFile(this.filePath, "utf8")).split(/\r?\n/).filter(Boolean);
      const events = lines.map((line) => JSON.parse(line) as UsageEvent);
      return tenantId ? events.filter((event) => event.tenantId === tenantId) : events;
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
      throw error;
    }
  }

  status() {
    return {
      enabled: config.featureFlags.billing,
      provider: "internal-metering-ledger",
      paymentGateway: "not_configured",
      mode: config.deploymentMode
    };
  }
}
