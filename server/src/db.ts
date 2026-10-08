import "dotenv/config";
import { Pool } from "pg";

// Read the PostgreSQL connection string from the server environment.
const connectionString = process.env.DATABASE_URL;

// Fail early during startup if the database connection is not configured.
if (!connectionString) {
  throw new Error("DATABASE_URL is not defined");
}

// Shared PostgreSQL connection pool used by the Express API routes.
export const pool = new Pool({
  connectionString,
});
