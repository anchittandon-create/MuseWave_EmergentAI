import { getApps, initializeApp, cert } from "firebase-admin/app";
import { getFirestore } from "firebase-admin/firestore";
import { getStorage } from "firebase-admin/storage";
import crypto from "crypto";

let cachedApp = null;

function resolveServiceAccount() {
  const rawJson = process.env.GOOGLE_APPLICATION_CREDENTIALS_JSON;
  if (rawJson) {
    try {
      const parsed = JSON.parse(rawJson);
      if (parsed.project_id && parsed.client_email && parsed.private_key) {
        return parsed;
      }
    } catch (error) {
      throw new Error("GOOGLE_APPLICATION_CREDENTIALS_JSON must be valid JSON");
    }
  }

  const projectId = process.env.FIREBASE_PROJECT_ID || process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT;
  const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
  const privateKeyRaw = process.env.FIREBASE_PRIVATE_KEY;

  if (projectId && clientEmail && privateKeyRaw) {
    return {
      project_id: projectId,
      client_email: clientEmail,
      private_key: privateKeyRaw.replace(/\\n/g, "\n"),
    };
  }

  return null;
}

function getBucketName() {
  const bucket = process.env.FIREBASE_STORAGE_BUCKET;
  if (!bucket) {
    throw new Error("Missing FIREBASE_STORAGE_BUCKET environment variable");
  }
  return bucket;
}

function getApp() {
  if (cachedApp) return cachedApp;
  if (getApps().length > 0) {
    cachedApp = getApps()[0];
    return cachedApp;
  }

  const serviceAccount = resolveServiceAccount();
  const bucketName = getBucketName();

  if (serviceAccount) {
    cachedApp = initializeApp({
      credential: cert(serviceAccount),
      storageBucket: bucketName,
    });
    return cachedApp;
  }

  cachedApp = initializeApp({
    storageBucket: bucketName,
  });
  return cachedApp;
}

export function getFirestoreDb() {
  return getFirestore(getApp());
}

export function getStorageBucket() {
  return getStorage(getApp()).bucket(getBucketName());
}

export function buildFirebaseStorageDownloadUrl(path, token) {
  const bucket = getBucketName();
  const encodedPath = encodeURIComponent(path);
  return `https://firebasestorage.googleapis.com/v0/b/${bucket}/o/${encodedPath}?alt=media&token=${token}`;
}

export async function uploadBufferToStorage({
  path,
  buffer,
  contentType,
  cacheControl = "no-store, max-age=0",
  token,
}) {
  if (!path) throw new Error("storage path is required");
  if (!buffer || !buffer.length) throw new Error("storage buffer is required");

  const bucket = getStorageBucket();
  const file = bucket.file(path);
  const stableToken = token || crypto.createHash("sha256").update(path).digest("hex");

  await file.save(buffer, {
    resumable: false,
    contentType,
    metadata: {
      cacheControl,
      contentType,
      metadata: {
        firebaseStorageDownloadTokens: stableToken,
      },
    },
    public: false,
    validation: false,
  });

  return {
    path,
    token: stableToken,
    url: buildFirebaseStorageDownloadUrl(path, stableToken),
  };
}

export async function downloadBufferFromStorage(path) {
  if (!path) throw new Error("storage path is required");
  const bucket = getStorageBucket();
  const file = bucket.file(path);
  const [buffer] = await file.download();
  return buffer;
}
