import { createHmac, randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { config } from "../config.js";
import type { PlatformIdentity } from "../types.js";

interface StoredUser {
  userId: string;
  tenantId: string;
  email: string;
  passwordHash: string;
  salt: string;
  roles: string[];
  createdAt: string;
}

interface TokenPayload {
  sub: string;
  tenantId: string;
  email: string;
  roles: string[];
  exp: number;
}

function b64url(input: Buffer | string): string {
  return Buffer.from(input).toString("base64url");
}

function usersPath(): string {
  return path.join(config.authRoot, "users.json");
}

async function loadUsers(): Promise<StoredUser[]> {
  try {
    return JSON.parse(await readFile(usersPath(), "utf8")) as StoredUser[];
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return [];
    throw error;
  }
}

async function saveUsers(users: StoredUser[]): Promise<void> {
  await mkdir(config.authRoot, { recursive: true });
  await writeFile(usersPath(), JSON.stringify(users, null, 2), "utf8");
}

function passwordHash(password: string, salt: string): string {
  return scryptSync(password, salt, 64).toString("hex");
}

function signToken(payload: TokenPayload): string {
  const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = b64url(JSON.stringify(payload));
  const signature = createHmac("sha256", config.authTokenSecret).update(`${header}.${body}`).digest("base64url");
  return `${header}.${body}.${signature}`;
}

function parseToken(token: string): TokenPayload | undefined {
  const [header, body, signature] = token.split(".");
  if (!header || !body || !signature) return undefined;
  const expected = createHmac("sha256", config.authTokenSecret).update(`${header}.${body}`).digest();
  const actual = Buffer.from(signature, "base64url");
  if (expected.length !== actual.length || !timingSafeEqual(expected, actual)) return undefined;
  const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as TokenPayload;
  if (!payload.exp || payload.exp < Math.floor(Date.now() / 1000)) return undefined;
  return payload;
}

export function personalIdentity(): PlatformIdentity {
  return {
    userId: "personal-user",
    tenantId: "personal-workspace",
    roles: ["owner", "admin"],
    anonymous: true
  };
}

export async function registerUser(email: string, password: string, tenantId?: string): Promise<PlatformIdentity> {
  if (!config.authAllowRegistration) throw new Error("AUTH_REGISTRATION_DISABLED");
  if (!email.includes("@") || password.length < 10) throw new Error("AUTH_INVALID_CREDENTIAL_FORMAT");
  const users = await loadUsers();
  const normalized = email.trim().toLowerCase();
  if (users.some((user) => user.email === normalized)) throw new Error("AUTH_EMAIL_EXISTS");
  const salt = randomBytes(16).toString("hex");
  const user: StoredUser = {
    userId: `usr_${randomBytes(8).toString("hex")}`,
    tenantId: tenantId?.trim() || `tenant_${randomBytes(6).toString("hex")}`,
    email: normalized,
    passwordHash: passwordHash(password, salt),
    salt,
    roles: ["owner"],
    createdAt: new Date().toISOString()
  };
  users.push(user);
  await saveUsers(users);
  return { userId: user.userId, tenantId: user.tenantId, email: user.email, roles: user.roles, anonymous: false };
}

export async function loginUser(email: string, password: string): Promise<{ token: string; identity: PlatformIdentity }> {
  const users = await loadUsers();
  const user = users.find((candidate) => candidate.email === email.trim().toLowerCase());
  if (!user) throw new Error("AUTH_INVALID_CREDENTIALS");
  const actual = Buffer.from(passwordHash(password, user.salt), "hex");
  const expected = Buffer.from(user.passwordHash, "hex");
  if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) throw new Error("AUTH_INVALID_CREDENTIALS");
  const exp = Math.floor(Date.now() / 1000) + config.authTokenTtlSeconds;
  const identity = { userId: user.userId, tenantId: user.tenantId, email: user.email, roles: user.roles, anonymous: false };
  return { token: signToken({ sub: user.userId, tenantId: user.tenantId, email: user.email, roles: user.roles, exp }), identity };
}

export function identityFromAuthorization(authorization?: string): PlatformIdentity | undefined {
  if (!authorization?.startsWith("Bearer ")) return undefined;
  const payload = parseToken(authorization.slice(7));
  if (!payload) return undefined;
  return { userId: payload.sub, tenantId: payload.tenantId, email: payload.email, roles: payload.roles, anonymous: false };
}
