import { MongoClient } from "mongodb";

const defaultDbName = process.env.MONGODB_DB_NAME || process.env.DB_NAME || "musewave_db";
const mongoUri = process.env.MONGODB_URI;

function getOrCreateMongoPromise() {
  if (!mongoUri) {
    throw new Error("Missing MONGODB_URI environment variable");
  }
  let cachedPromise = globalThis.__musewaveMongoPromise;
  if (!cachedPromise) {
    const client = new MongoClient(mongoUri, {});
    cachedPromise = client.connect();
    globalThis.__musewaveMongoPromise = cachedPromise;
  }
  return cachedPromise;
}

export async function getMongoDb(dbName = defaultDbName) {
  const cachedPromise = getOrCreateMongoPromise();
  const client = await cachedPromise;
  return client.db(dbName);
}

export async function getMongoCollection(collectionName, dbName = defaultDbName) {
  if (!String(collectionName || "").trim()) {
    throw new Error("collectionName is required");
  }
  const db = await getMongoDb(dbName);
  return db.collection(collectionName);
}

export default getOrCreateMongoPromise;
