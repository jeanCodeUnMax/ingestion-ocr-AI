import assert from "node:assert/strict";
import test from "node:test";
import { normalizeRecipe, recipeForProfile } from "../src/core/recipe.js";

test("les profils de traitement restent explicites et personnalisables", () => {
  const quick = recipeForProfile("quick");
  const standard = recipeForProfile("standard");
  assert.equal(quick.kentRealityCheck, false);
  assert.equal(standard.kentRealityCheck, true);
  const custom = normalizeRecipe({ profile: "custom", pseudocode: false, atomicFacts: true });
  assert.equal(custom.profile, "custom");
  assert.equal(custom.pseudocode, false);
  assert.equal(custom.atomicFacts, true);
  assert.equal(custom.embeddings, true);
});
