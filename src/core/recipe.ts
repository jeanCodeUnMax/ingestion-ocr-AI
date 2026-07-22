import type { ProcessingRecipe, RecipeProfile } from "../types.js";

const PROFILES: Record<Exclude<RecipeProfile, "custom">, ProcessingRecipe> = {
  quick: {
    profile: "quick",
    semanticAnalysis: true,
    maieuticAnalysis: false,
    kentRealityCheck: false,
    pseudocode: false,
    synthesis: true,
    shrink: true,
    atomicFacts: false,
    tagsAndTaxonomy: true,
    embeddings: true,
    visualDescriptions: true,
    translation: false
  },
  standard: {
    profile: "standard",
    semanticAnalysis: true,
    maieuticAnalysis: true,
    kentRealityCheck: true,
    pseudocode: true,
    synthesis: true,
    shrink: true,
    atomicFacts: true,
    tagsAndTaxonomy: true,
    embeddings: true,
    visualDescriptions: true,
    translation: false
  },
  deep: {
    profile: "deep",
    semanticAnalysis: true,
    maieuticAnalysis: true,
    kentRealityCheck: true,
    pseudocode: true,
    synthesis: true,
    shrink: true,
    atomicFacts: true,
    tagsAndTaxonomy: true,
    embeddings: true,
    visualDescriptions: true,
    translation: true
  }
};

export function recipeForProfile(profile: RecipeProfile): ProcessingRecipe {
  if (profile === "custom") return { ...PROFILES.standard, profile: "custom" };
  return { ...PROFILES[profile] };
}

export function normalizeRecipe(input: Partial<ProcessingRecipe> | undefined, fallback: RecipeProfile = "standard"): ProcessingRecipe {
  const profile = input?.profile ?? fallback;
  const base = recipeForProfile(profile);
  return {
    ...base,
    ...input,
    profile
  };
}
