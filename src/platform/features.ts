import { config } from "../config.js";
import type { FeatureName, InputKind } from "../types.js";

const inputFeatureMap: Partial<Record<InputKind, FeatureName>> = {
  word: "word",
  excel: "excel",
  csv: "csv",
  json: "json",
  markdown: "markdown",
  text: "text",
  image: "image",
  audio: "audio",
  svg: "svg"
};

export function isFeatureEnabled(name: FeatureName): boolean {
  return config.featureFlags[name];
}

export function assertFeature(name: FeatureName): void {
  if (!isFeatureEnabled(name)) {
    throw new Error(`FEATURE_DISABLED:${name}`);
  }
}

export function assertInputKindEnabled(kind: InputKind): void {
  const feature = inputFeatureMap[kind];
  if (feature) assertFeature(feature);
}

export function platformStatus() {
  return {
    deploymentMode: config.deploymentMode,
    features: config.featureFlags,
    decisions: {
      auth: config.featureFlags.auth ? "enabled" : "prepared_disabled",
      billing: config.featureFlags.billing ? "enabled" : "prepared_disabled",
      multiTenant: config.featureFlags.multiTenant ? "enabled" : "prepared_disabled"
    }
  };
}
