import { MongoClient } from "mongodb";

const uri = process.env.MONGODB_URI;
if (!uri) {
  throw new Error("Missing MONGODB_URI environment variable");
}

const options = {};

let client;
let clientPromise;

if (process.env.NODE_ENV === "development") {
  if (!global._musewaveMongoClientPromise) {
    client = new MongoClient(uri, options);
    global._musewaveMongoClientPromise = client.connect();
  }
  clientPromise = global._musewaveMongoClientPromise;
} else {
  client = new MongoClient(uri, options);
  clientPromise = client.connect();
}

export async function getMongoDb(dbName = "musewave_db") {
  const connectedClient = await clientPromise;
  return connectedClient.db(dbName);
}

export default clientPromise;
