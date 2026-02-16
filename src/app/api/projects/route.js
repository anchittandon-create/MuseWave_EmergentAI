import { NextResponse } from "next/server";
import { getMongoCollection } from "../../../lib/mongodb";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const parseIsoDate = (value, fieldName) => {
  if (!value) {
    throw new Error(`Missing ${fieldName} environment variable`);
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    throw new Error(`${fieldName} must be a valid ISO date`);
  }
  return parsed;
};

export async function GET() {
  try {
    const appCreationDate = parseIsoDate(process.env.APP_CREATION_DATE, "APP_CREATION_DATE");
    const now = new Date();

    const projectsCollection = await getMongoCollection("projects");
    const query = {
      created_at: {
        $gte: appCreationDate,
        $lte: now,
      },
    };

    const projects = await projectsCollection.find(query).sort({ created_at: -1 }).toArray();

    const serialized = projects.map((project) => ({
      ...project,
      _id: String(project._id),
      created_at: new Date(project.created_at).toISOString(),
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
        error: error instanceof Error ? error.message : "project query failed",
      },
      { status: 500 }
    );
  }
}
