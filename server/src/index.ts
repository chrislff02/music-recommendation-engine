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

app.get("/api/songs", async (_req, res) => {
  try {
    const result = await pool.query(`
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
      ORDER BY s.id
      LIMIT 10
    `);

    res.json(result.rows);
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
