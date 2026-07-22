import { readFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import type { AudioProviderId } from "../types.js";

export interface AudioTranscript {
  provider: Exclude<AudioProviderId, "none">;
  model: string;
  text: string;
  language?: string;
  durationSeconds?: number;
  raw?: unknown;
}

function transcriptText(payload: unknown): string {
  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    if (typeof record.text === "string") return record.text;
    if (typeof record.transcription === "string") return record.transcription;
    if (Array.isArray(record.segments)) {
      return record.segments.map((segment) => {
        if (segment && typeof segment === "object" && typeof (segment as Record<string, unknown>).text === "string") {
          return (segment as Record<string, unknown>).text as string;
        }
        return "";
      }).filter(Boolean).join(" ");
    }
  }
  return "";
}

async function uploadForm(filePath: string, extra: Record<string, string>): Promise<FormData> {
  const form = new FormData();
  const bytes = await readFile(filePath);
  form.append("file", new Blob([bytes]), path.basename(filePath));
  for (const [key, value] of Object.entries(extra)) form.append(key, value);
  return form;
}

export async function transcribeAudio(filePath: string, provider: AudioProviderId): Promise<AudioTranscript> {
  if (provider === "none") throw new Error("AUDIO_TRANSCRIPTION_PROVIDER_NOT_CONFIGURED");
  if (provider === "mistral") {
    if (!config.mistral.apiKey) throw new Error("MISTRAL_API_KEY est obligatoire pour la transcription audio.");
    const body = await uploadForm(filePath, { model: config.mistral.audioModel, diarize: "false" });
    const response = await fetch(`${config.mistral.baseUrl}/audio/transcriptions`, {
      method: "POST",
      headers: { authorization: `Bearer ${config.mistral.apiKey}` },
      body,
      signal: AbortSignal.timeout(config.mistral.timeoutMs)
    });
    if (!response.ok) throw new Error(`MISTRAL_AUDIO_HTTP_${response.status}:${(await response.text()).slice(0, 1000)}`);
    const raw = await response.json();
    const text = transcriptText(raw);
    if (!text.trim()) throw new Error("MISTRAL_AUDIO_EMPTY_TRANSCRIPT");
    const record = raw as Record<string, unknown>;
    return {
      provider,
      model: config.mistral.audioModel,
      text,
      ...(typeof record.language === "string" ? { language: record.language } : {}),
      ...(typeof record.duration === "number" ? { durationSeconds: record.duration } : {}),
      raw
    };
  }

  const body = await uploadForm(filePath, {
    response_format: "json",
    temperature: "0.0",
    language: config.whisperCpp.language
  });
  const response = await fetch(`${config.whisperCpp.baseUrl}/inference`, {
    method: "POST",
    body,
    signal: AbortSignal.timeout(config.whisperCpp.timeoutMs)
  });
  if (!response.ok) throw new Error(`WHISPER_CPP_HTTP_${response.status}:${(await response.text()).slice(0, 1000)}`);
  const contentType = response.headers.get("content-type") ?? "";
  const raw = contentType.includes("json") ? await response.json() : { text: await response.text() };
  const text = transcriptText(raw);
  if (!text.trim()) throw new Error("WHISPER_CPP_EMPTY_TRANSCRIPT");
  return { provider, model: "whisper.cpp", text, raw };
}
