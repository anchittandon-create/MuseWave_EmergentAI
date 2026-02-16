import { NextResponse } from "next/server";
import { getMongoDb } from "../../../lib/mongodb";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const getDefaultDateRange = () => {
  const rawCreationDate = process.env.APP_CREATION_DATE;
  if (!rawCreationDate) {
    throw new Error("Missing APP_CREATION_DATE environment variable");
  }

  const appCreationDate = new Date(rawCreationDate);
  if (Number.isNaN(appCreationDate.getTime())) {
    throw new Error("Invalid APP_CREATION_DATE. Expected ISO date string.");
  }

  const now = new Date();
  return { appCreationDate, now };
};

export async function GET() {
  try {
    const { appCreationDate, now } = getDefaultDateRange();

    const db = await getMongoDb();
    const query = {
      created_at: {
        $gte: appCreationDate,
        $lte: now,
      },
    };

    const projects = await db
      .collection("projects")
      .find(query)
      .sort({ created_at: -1 })
      .toArray();

    const serialized = projects.map((project) => ({
      ...project,
      _id: String(project._id),
    }));

    return NextResponse.json(
      {
        projects: serialized,
        filter: {
          start_date: appCreationDate.toISOString(),
          end_date: now.toISOString(),
        },
      },
      { status: 200 }
    );
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Failed to fetch projects",
      },
      { status: 500 }
    );
  }
}
