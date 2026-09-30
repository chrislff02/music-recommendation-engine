import express from "express";
import cors from "cors";

import { pool } from "./db";

const app = express();
const PORT = 5001;

app.use(cors());
app.use(express.json());

app.get("/api/health", (_req, res) => {
  res.json({ status: "ok" });
});

app.get("/api/songs", async (req, res) => {
  try {
    const page = Math.max(Number(req.query.page) || 1, 1);
    const limit = Math.min(Math.max(Number(req.query.limit) || 20, 1), 100);

    const search =
      typeof req.query.search === "string" ? req.query.search.trim() : "";

    const genre =
      typeof req.query.genre === "string" ? req.query.genre.trim() : "";

    const offset = (page - 1) * limit;

    const whereConditions: string[] = [];
    const values: Array<string | number> = [];

    if (search) {
      values.push(`%${search}%`);
      const searchParam = `$${values.length}`;

      whereConditions.push(`
        (
          s.title ILIKE ${searchParam}
          OR a.name ILIKE ${searchParam}
        )
      `);
    }

    if (genre) {
      values.push(genre);
      const genreParam = `$${values.length}`;

      whereConditions.push(`g.name = ${genreParam}`);
    }

    const whereClause =
      whereConditions.length > 0
        ? `WHERE ${whereConditions.join(" AND ")}`
        : "";

    const countQuery = `
      SELECT COUNT(*)::int AS total
      FROM "Song" s
      JOIN "Artist" a
        ON s."artistId" = a.id
      LEFT JOIN "Genre" g
        ON s."genreId" = g.id
      ${whereClause}
    `;

    const countResult = await pool.query(countQuery, values);

    values.push(limit);
    const limitParam = `$${values.length}`;

    values.push(offset);
    const offsetParam = `$${values.length}`;

    const songsQuery = `
      SELECT
        s.id,
        s.title,
        s."externalId",
        s.tempo,
        s.energy,
        s.danceability,
        s.valence,
        s.acousticness,
        s.instrumentalness,
        s.speechiness,
        s.liveness,
        s.popularity,
        s.duration,
        a.name AS artist,
        g.name AS genre
      FROM "Song" s
      JOIN "Artist" a
        ON s."artistId" = a.id
      LEFT JOIN "Genre" g
        ON s."genreId" = g.id
      ${whereClause}
      ORDER BY s.id
      LIMIT ${limitParam}
      OFFSET ${offsetParam}
    `;

    const songsResult = await pool.query(songsQuery, values);

    const total = countResult.rows[0].total;
    const totalPages = Math.ceil(total / limit);

    res.json({
      page,
      limit,
      total,
      totalPages,
      songs: songsResult.rows,
    });
  } catch (error) {
    console.error("Failed to fetch songs:", error);

    res.status(500).json({
      error: "Failed to fetch songs",
    });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
