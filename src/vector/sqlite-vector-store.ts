import { DatabaseSync } from "node:sqlite";
import path from "node:path";
import { ensureDir } from "../utils/files.js";
import type { StoredVectorChunk, VectorSearchResult } from "../types.js";

function cosineSimilarity(a: number[], b: number[]): number {
  const length = Math.min(a.length, b.length);
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let index = 0; index < length; index += 1) {
    const av = a[index] ?? 0;
    const bv = b[index] ?? 0;
    dot += av * bv;
    normA += av * av;
    normB += bv * bv;
  }
  if (normA === 0 || normB === 0) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

interface ChunkRow {
  chunk_id: string;
  document_id: string;
  page_start: number;
  page_end: number;
  content_type: string;
  heading: string | null;
  text: string;
  source_hash: string;
  embedding_model: string;
  dimension: number;
  embedding_json: string;
  created_at: string;
}

export class SqliteVectorStore {
  private database: DatabaseSync | undefined;

  constructor(private readonly filePath: string) {}

  async initialize(): Promise<void> {
    await ensureDir(path.dirname(this.filePath));
    this.database = new DatabaseSync(this.filePath);
    this.database.exec(`
      PRAGMA journal_mode = WAL;
      PRAGMA synchronous = NORMAL;
      CREATE TABLE IF NOT EXISTS vector_chunks (
        chunk_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        page_start INTEGER NOT NULL,
        page_end INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        heading TEXT,
        text TEXT NOT NULL,
        source_hash TEXT NOT NULL,
        embedding_model TEXT NOT NULL,
        dimension INTEGER NOT NULL,
        embedding_json TEXT NOT NULL,
        created_at TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_vector_chunks_document
      ON vector_chunks(document_id);
    `);
  }

  private db(): DatabaseSync {
    if (!this.database) throw new Error("La base vectorielle SQLite n'est pas initialisée.");
    return this.database;
  }

  upsertMany(chunks: StoredVectorChunk[]): void {
    if (chunks.length === 0) return;
    const database = this.db();
    const statement = database.prepare(`
      INSERT INTO vector_chunks (
        chunk_id, document_id, page_start, page_end, content_type, heading,
        text, source_hash, embedding_model, dimension, embedding_json, created_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(chunk_id) DO UPDATE SET
        document_id = excluded.document_id,
        page_start = excluded.page_start,
        page_end = excluded.page_end,
        content_type = excluded.content_type,
        heading = excluded.heading,
        text = excluded.text,
        source_hash = excluded.source_hash,
        embedding_model = excluded.embedding_model,
        dimension = excluded.dimension,
        embedding_json = excluded.embedding_json,
        created_at = excluded.created_at
    `);
    database.exec("BEGIN IMMEDIATE");
    try {
      for (const chunk of chunks) {
        statement.run(
          chunk.chunkId,
          chunk.documentId,
          chunk.pageStart,
          chunk.pageEnd,
          chunk.contentType,
          chunk.heading ?? null,
          chunk.text,
          chunk.sourceHash,
          chunk.embeddingModel,
          chunk.dimension,
          JSON.stringify(chunk.embedding),
          chunk.createdAt
        );
      }
      database.exec("COMMIT");
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    }
  }

  deleteDocument(documentId: string): number {
    const result = this.db().prepare("DELETE FROM vector_chunks WHERE document_id = ?").run(documentId);
    return Number(result.changes);
  }

  count(documentId?: string): number {
    const row = documentId
      ? this.db().prepare("SELECT COUNT(*) AS count FROM vector_chunks WHERE document_id = ?").get(documentId) as { count: number }
      : this.db().prepare("SELECT COUNT(*) AS count FROM vector_chunks").get() as { count: number };
    return Number(row.count);
  }

  listDocumentChunks(documentId: string, limit = 1000): Omit<StoredVectorChunk, "embedding">[] {
    const rows = this.db().prepare(`
      SELECT chunk_id, document_id, page_start, page_end, content_type, heading,
             text, source_hash, embedding_model, dimension, created_at
      FROM vector_chunks
      WHERE document_id = ?
      ORDER BY page_start, chunk_id
      LIMIT ?
    `).all(documentId, limit) as Array<Omit<ChunkRow, "embedding_json">>;
    return rows.map((row) => ({
      chunkId: row.chunk_id,
      documentId: row.document_id,
      pageStart: row.page_start,
      pageEnd: row.page_end,
      contentType: row.content_type as StoredVectorChunk["contentType"],
      ...(row.heading ? { heading: row.heading } : {}),
      text: row.text,
      sourceHash: row.source_hash,
      embeddingModel: row.embedding_model,
      dimension: row.dimension,
      createdAt: row.created_at
    }));
  }

  searchDocuments(queryVector: number[], documentIds: string[], options?: { embeddingModel?: string; limit?: number; minScore?: number }): VectorSearchResult[] {
    const allowed = new Set(documentIds);
    if (allowed.size === 0) return [];
    const limit = Math.max(1, Math.min(options?.limit ?? 8, 100));
    const minScore = options?.minScore ?? -1;
    const rows = (options?.embeddingModel
      ? this.db().prepare("SELECT * FROM vector_chunks WHERE embedding_model = ?").all(options.embeddingModel)
      : this.db().prepare("SELECT * FROM vector_chunks").all()) as unknown as ChunkRow[];
    return rows
      .filter((row) => allowed.has(row.document_id))
      .map((row) => ({
        chunkId: row.chunk_id,
        documentId: row.document_id,
        pageStart: row.page_start,
        pageEnd: row.page_end,
        contentType: row.content_type,
        ...(row.heading ? { heading: row.heading } : {}),
        text: row.text,
        score: cosineSimilarity(queryVector, JSON.parse(row.embedding_json) as number[])
      }))
      .filter((row) => row.score >= minScore)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  search(queryVector: number[], options?: { documentId?: string; embeddingModel?: string; limit?: number; minScore?: number }): VectorSearchResult[] {
    const limit = Math.max(1, Math.min(options?.limit ?? 8, 100));
    const minScore = options?.minScore ?? -1;
    let rows: ChunkRow[];
    if (options?.documentId && options.embeddingModel) {
      rows = this.db().prepare(
        "SELECT * FROM vector_chunks WHERE document_id = ? AND embedding_model = ?"
      ).all(options.documentId, options.embeddingModel) as unknown as ChunkRow[];
    } else if (options?.documentId) {
      rows = this.db().prepare(
        "SELECT * FROM vector_chunks WHERE document_id = ?"
      ).all(options.documentId) as unknown as ChunkRow[];
    } else if (options?.embeddingModel) {
      rows = this.db().prepare(
        "SELECT * FROM vector_chunks WHERE embedding_model = ?"
      ).all(options.embeddingModel) as unknown as ChunkRow[];
    } else {
      rows = this.db().prepare("SELECT * FROM vector_chunks").all() as unknown as ChunkRow[];
    }

    return rows
      .map((row) => ({
        chunkId: row.chunk_id,
        documentId: row.document_id,
        pageStart: row.page_start,
        pageEnd: row.page_end,
        contentType: row.content_type,
        ...(row.heading ? { heading: row.heading } : {}),
        text: row.text,
        score: cosineSimilarity(queryVector, JSON.parse(row.embedding_json) as number[])
      }))
      .filter((row) => row.score >= minScore)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit);
  }

  close(): void {
    this.database?.close();
    this.database = undefined;
  }
}
