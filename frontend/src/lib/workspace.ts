// Remembers the visitor's demo workspace key for its 24-hour lifetime.

const STORAGE_KEY = "sanad.workspace";
const LIFETIME_MS = 24 * 60 * 60 * 1000;

type Saved = { key: string; createdAt: number };

export function loadWorkspaceKey(): string | null {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Saved | null;
    if (saved && Date.now() - saved.createdAt < LIFETIME_MS) return saved.key;
  } catch {
    // unreadable or blocked storage: start fresh
  }
  return null;
}

export function saveWorkspaceKey(key: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ key, createdAt: Date.now() } satisfies Saved));
  } catch {
    // the workspace still works for this visit
  }
}

export function clearWorkspaceKey(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
