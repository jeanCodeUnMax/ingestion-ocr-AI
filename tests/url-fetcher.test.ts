import assert from "node:assert/strict";
import test from "node:test";
import { assertPublicUrlSyntax, htmlToMarkdown } from "../src/ingestion/url-fetcher.js";

test("les URL locales et privées sont refusées avant téléchargement", () => {
  assert.throws(() => assertPublicUrlSyntax("http://localhost/admin"), /PRIVATE_HOST/);
  assert.throws(() => assertPublicUrlSyntax("http://127.0.0.1/secret"), /PRIVATE_IP/);
  assert.throws(() => assertPublicUrlSyntax("file:///etc/passwd"), /PROTOCOL/);
  assert.equal(assertPublicUrlSyntax("https://example.com/report.pdf").hostname, "example.com");
});

test("une page HTML est normalisée en Markdown avec sa provenance", () => {
  const markdown = htmlToMarkdown("<html><title>Guide 5S</title><body><h1>Trier</h1><p>Supprimer l'inutile.</p><script>ignore()</script></body></html>", "https://example.com/5s");
  assert.match(markdown, /# Guide 5S/);
  assert.match(markdown, /source_url=https:\/\/example.com\/5s/);
  assert.match(markdown, /Supprimer l'inutile/);
  assert.doesNotMatch(markdown, /ignore\(\)/);
});
