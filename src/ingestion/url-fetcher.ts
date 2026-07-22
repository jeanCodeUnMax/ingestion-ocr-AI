import { lookup } from "node:dns/promises";
import { isIP } from "node:net";

export interface UrlFetchResult {
  finalUrl: string;
  filename: string;
  mimeType: string;
  body: Buffer;
}

function privateIpv4(ip: string): boolean {
  const parts = ip.split(".").map(Number);
  if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part))) return true;
  const [a, b] = parts as [number, number, number, number];
  return a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168) || a >= 224;
}

function privateIpv6(ip: string): boolean {
  const normalized = ip.toLowerCase();
  return normalized === "::1" || normalized === "::" || normalized.startsWith("fc") || normalized.startsWith("fd") || normalized.startsWith("fe8") || normalized.startsWith("fe9") || normalized.startsWith("fea") || normalized.startsWith("feb");
}

export function assertPublicUrlSyntax(rawUrl: string): URL {
  let url: URL;
  try { url = new URL(rawUrl); } catch { throw new Error("URL_INVALID"); }
  if (url.protocol !== "http:" && url.protocol !== "https:") throw new Error("URL_PROTOCOL_NOT_ALLOWED");
  if (url.username || url.password) throw new Error("URL_CREDENTIALS_NOT_ALLOWED");
  const hostname = url.hostname.toLowerCase();
  if (hostname === "localhost" || hostname.endsWith(".localhost") || hostname.endsWith(".local")) throw new Error("URL_PRIVATE_HOST_NOT_ALLOWED");
  if (isIP(hostname) === 4 && privateIpv4(hostname)) throw new Error("URL_PRIVATE_IP_NOT_ALLOWED");
  if (isIP(hostname) === 6 && privateIpv6(hostname)) throw new Error("URL_PRIVATE_IP_NOT_ALLOWED");
  return url;
}

export async function assertPublicDns(url: URL): Promise<void> {
  if (isIP(url.hostname)) return;
  const records = await lookup(url.hostname, { all: true, verbatim: true });
  if (records.length === 0) throw new Error("URL_DNS_EMPTY");
  for (const record of records) {
    if ((record.family === 4 && privateIpv4(record.address)) || (record.family === 6 && privateIpv6(record.address))) {
      throw new Error("URL_DNS_RESOLVES_TO_PRIVATE_IP");
    }
  }
}

function filenameFrom(url: URL, mimeType: string): string {
  const candidate = decodeURIComponent(url.pathname.split("/").filter(Boolean).at(-1) ?? "").replace(/[^a-zA-Z0-9._-]+/g, "_");
  if (candidate.includes(".")) return candidate;
  const extension = mimeType.includes("pdf") ? ".pdf" : mimeType.includes("json") ? ".json" : mimeType.includes("csv") ? ".csv" : mimeType.includes("markdown") ? ".md" : ".html";
  return `${candidate || "download"}${extension}`;
}

export async function fetchPublicDocument(rawUrl: string, options: { maxBytes: number; maxRedirects?: number; timeoutMs?: number }): Promise<UrlFetchResult> {
  let current = assertPublicUrlSyntax(rawUrl);
  const maxRedirects = options.maxRedirects ?? 3;
  for (let redirect = 0; redirect <= maxRedirects; redirect += 1) {
    await assertPublicDns(current);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 30000);
    let response: Response;
    try {
      response = await fetch(current, { redirect: "manual", signal: controller.signal, headers: { "user-agent": "OCR-AI-System/0.6" } });
    } finally {
      clearTimeout(timeout);
    }
    if ([301, 302, 303, 307, 308].includes(response.status)) {
      const location = response.headers.get("location");
      if (!location) throw new Error("URL_REDIRECT_WITHOUT_LOCATION");
      current = assertPublicUrlSyntax(new URL(location, current).toString());
      continue;
    }
    if (!response.ok) throw new Error(`URL_FETCH_FAILED:${response.status}`);
    const contentLength = Number.parseInt(response.headers.get("content-length") ?? "0", 10);
    if (contentLength > options.maxBytes) throw new Error("URL_CONTENT_TOO_LARGE");
    const bytes = Buffer.from(await response.arrayBuffer());
    if (bytes.length > options.maxBytes) throw new Error("URL_CONTENT_TOO_LARGE");
    const mimeType = (response.headers.get("content-type") ?? "application/octet-stream").split(";")[0]?.trim() || "application/octet-stream";
    return { finalUrl: current.toString(), filename: filenameFrom(current, mimeType), mimeType, body: bytes };
  }
  throw new Error("URL_TOO_MANY_REDIRECTS");
}

export function htmlToMarkdown(html: string, sourceUrl: string): string {
  const title = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.replace(/\s+/g, " ").trim() || sourceUrl;
  const cleaned = html
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, "")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, "")
    .replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/gi, "")
    .replace(/<(h[1-6])\b[^>]*>([\s\S]*?)<\/\1>/gi, (_m, tag: string, body: string) => `${"#".repeat(Number(tag[1]))} ${body}\n\n`)
    .replace(/<li\b[^>]*>([\s\S]*?)<\/li>/gi, "- $1\n")
    .replace(/<br\s*\/?>/gi, "\n")
    .replace(/<\/p>/gi, "\n\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
  return `# ${title}\n\n<!-- source_url=${sourceUrl} -->\n\n${cleaned}\n`;
}
