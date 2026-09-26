// Minimal .env loader (no external deps).
import { readFileSync } from "node:fs";

const cache = new Map<string, string>();

export function loadEnv(path: string): void {
  const text = readFileSync(path, "utf8");
  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    const val = trimmed.slice(eq + 1).trim();
    if (!cache.has(key)) cache.set(key, val);
  }
}

export function env(key: string): string {
  const v = cache.get(key) ?? process.env[key] ?? "";
  if (!v) throw new Error(`Missing required env var: ${key}`);
  return v;
}

export function envOptional(key: string): string {
  return cache.get(key) ?? process.env[key] ?? "";
}
