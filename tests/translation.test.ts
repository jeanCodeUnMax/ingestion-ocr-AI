import assert from "node:assert/strict";
import test from "node:test";
import { splitTranslationSegments } from "../src/translation/pipeline.js";

test("la traduction découpe sans perdre les paragraphes", () => {
  const source = ["# Titre", "Premier paragraphe.", "Deuxième paragraphe avec une valeur 42.", "Troisième paragraphe."].join("\n\n");
  const segments = splitTranslationSegments(source, 45);
  assert.ok(segments.length >= 2);
  const rebuilt = segments.join("\n\n");
  assert.match(rebuilt, /Premier paragraphe/);
  assert.match(rebuilt, /valeur 42/);
  assert.match(rebuilt, /Troisième paragraphe/);
});
