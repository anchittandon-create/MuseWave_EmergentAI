import { promises as fs } from "fs";
import path from "path";

type UserRecord = {
  id: string;
  name: string;
  mobile: string;
  phoneNumber: string;
  role: string;
  created_at: string;
};

type TrackRecord = {
  id: string;
  user_id: string;
  title: string;
  music_prompt: string;
  genres: string[];
  duration_seconds: number;
  artist_inspiration: string;
  lyrics?: string;
  audio_url: string;
  video_url?: string | null;
  cover_art_url: string;
  created_at: string;
};

type StoreShape = {
  users: Record<string, UserRecord>;
  tracks: Record<string, TrackRecord>;
};

const STORE_PATH = path.join("/tmp", "musewave-store.json");

const EMPTY_STORE: StoreShape = {
  users: {},
  tracks: {},
};

async function readStore(): Promise<StoreShape> {
  try {
    const raw = await fs.readFile(STORE_PATH, "utf8");
    const parsed = JSON.parse(raw) as StoreShape;
    return {
      users: parsed?.users || {},
      tracks: parsed?.tracks || {},
    };
  } catch {
    return { ...EMPTY_STORE };
  }
}

async function writeStore(store: StoreShape): Promise<void> {
  await fs.writeFile(STORE_PATH, JSON.stringify(store), "utf8");
}

export function normalizeMobile(value: string): string {
  return String(value || "").replace(/\D+/g, "");
}

export async function upsertUser(input: {
  id: string;
  name: string;
  mobile: string;
  role?: string;
}): Promise<UserRecord> {
  const store = await readStore();
  const now = new Date().toISOString();
  const existing = store.users[input.id];
  const user: UserRecord = {
    id: input.id,
    name: input.name || existing?.name || "User",
    mobile: input.mobile,
    phoneNumber: input.mobile,
    role: input.role || existing?.role || "User",
    created_at: existing?.created_at || now,
  };
  store.users[user.id] = user;
  await writeStore(store);
  return user;
}

export async function getUserById(userId: string): Promise<UserRecord | null> {
  const store = await readStore();
  return store.users[userId] || null;
}

export async function findUserByMobile(mobile: string): Promise<UserRecord | null> {
  const normalized = normalizeMobile(mobile);
  if (!normalized) return null;
  const store = await readStore();
  return Object.values(store.users).find((user) => user.mobile === normalized) || null;
}

export async function saveTrack(track: TrackRecord): Promise<void> {
  const store = await readStore();
  store.tracks[track.id] = track;
  await writeStore(store);
}

export async function listTracksByUser(userId: string): Promise<TrackRecord[]> {
  const store = await readStore();
  return Object.values(store.tracks)
    .filter((track) => track.user_id === userId)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}

export async function listAllTracks(): Promise<TrackRecord[]> {
  const store = await readStore();
  return Object.values(store.tracks).sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
}

export async function listUsers(): Promise<UserRecord[]> {
  const store = await readStore();
  return Object.values(store.users);
}

export async function getTrackById(trackId: string): Promise<TrackRecord | null> {
  const store = await readStore();
  return store.tracks[trackId] || null;
}
