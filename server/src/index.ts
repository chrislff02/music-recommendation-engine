import express from "express";
import cors from "cors";
import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";

import { pool } from "./db";

import { requireAuth, type AuthenticatedRequest } from "./middleware/auth";

import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

const app = express();
const PORT = 5001;
const execFileAsync = promisify(execFile);

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

app.post("/api/auth/register", async (req, res) => {
  try {
    const { email, username, password } = req.body;

    if (!email || !username || !password) {
      return res.status(400).json({
        error: "Email, username, and password are required",
      });
    }

    if (password.length < 8) {
      return res.status(400).json({
        error: "Password must be at least 8 characters long",
      });
    }

    const existingUser = await pool.query(
      `
      SELECT id
      FROM "User"
      WHERE email = $1 OR username = $2
      LIMIT 1
      `,
      [email, username],
    );

    if (existingUser.rows.length > 0) {
      return res.status(409).json({
        error: "Email or username is already in use",
      });
    }

    const passwordHash = await bcrypt.hash(password, 12);

    const result = await pool.query(
      `
      INSERT INTO "User" (
        email,
        username,
        "passwordHash",
        "updatedAt"
      )
      VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
      RETURNING id, email, username, "createdAt"
      `,
      [email, username, passwordHash],
    );

    const user = result.rows[0];

    const jwtSecret = process.env.JWT_SECRET;

    if (!jwtSecret) {
      throw new Error("JWT_SECRET is not defined");
    }

    const token = jwt.sign(
      {
        userId: user.id,
      },
      jwtSecret,
      {
        expiresIn: "7d",
      },
    );

    return res.status(201).json({
      user,
      token,
    });
  } catch (error) {
    console.error("Failed to register user:", error);

    return res.status(500).json({
      error: "Failed to register user",
    });
  }
});

app.post("/api/auth/login", async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        error: "Email and password are required",
      });
    }

    const result = await pool.query(
      `
      SELECT
        id,
        email,
        username,
        "passwordHash",
        "createdAt"
      FROM "User"
      WHERE email = $1
      LIMIT 1
      `,
      [email],
    );

    if (result.rows.length === 0) {
      return res.status(401).json({
        error: "Invalid email or password",
      });
    }

    const user = result.rows[0];

    const passwordMatches = await bcrypt.compare(password, user.passwordHash);

    if (!passwordMatches) {
      return res.status(401).json({
        error: "Invalid email or password",
      });
    }

    const jwtSecret = process.env.JWT_SECRET;

    if (!jwtSecret) {
      throw new Error("JWT_SECRET is not defined");
    }

    const token = jwt.sign(
      {
        userId: user.id,
      },
      jwtSecret,
      {
        expiresIn: "7d",
      },
    );

    return res.json({
      user: {
        id: user.id,
        email: user.email,
        username: user.username,
        createdAt: user.createdAt,
      },
      token,
    });
  } catch (error) {
    console.error("Failed to log in:", error);

    return res.status(500).json({
      error: "Failed to log in",
    });
  }
});

app.get("/api/auth/me", requireAuth, async (req: AuthenticatedRequest, res) => {
  try {
    const result = await pool.query(
      `
        SELECT
          id,
          email,
          username,
          "createdAt"
        FROM "User"
        WHERE id = $1
        `,
      [req.userId],
    );

    if (result.rows.length === 0) {
      return res.status(404).json({
        error: "User not found",
      });
    }

    return res.json({
      user: result.rows[0],
    });
  } catch (error) {
    console.error("Failed to fetch current user:", error);

    return res.status(500).json({
      error: "Failed to fetch current user",
    });
  }
});

app.post(
  "/api/ratings",
  requireAuth,
  async (req: AuthenticatedRequest, res) => {
    try {
      const { songId, value } = req.body;

      if (!songId || !value) {
        return res.status(400).json({
          error: "songId and value are required",
        });
      }

      if (!Number.isInteger(value) || value < 1 || value > 5) {
        return res.status(400).json({
          error: "Rating must be an integer from 1 to 5",
        });
      }

      const songResult = await pool.query(
        `
        SELECT id
        FROM "Song"
        WHERE id = $1
        `,
        [songId],
      );

      if (songResult.rows.length === 0) {
        return res.status(404).json({
          error: "Song not found",
        });
      }

      const result = await pool.query(
        `
        INSERT INTO "Rating" (
          value,
          "userId",
          "songId",
          "updatedAt"
        )
        VALUES ($1, $2, $3, CURRENT_TIMESTAMP)

        ON CONFLICT ("userId", "songId")
        DO UPDATE SET
          value = EXCLUDED.value,
          "updatedAt" = CURRENT_TIMESTAMP

        RETURNING
          id,
          value,
          "userId",
          "songId",
          "createdAt",
          "updatedAt"
        `,
        [value, req.userId, songId],
      );

      return res.json({
        rating: result.rows[0],
      });
    } catch (error) {
      console.error("Failed to save rating:", error);

      return res.status(500).json({
        error: "Failed to save rating",
      });
    }
  },
);

app.get(
  "/api/ratings/me",
  requireAuth,
  async (req: AuthenticatedRequest, res) => {
    try {
      const result = await pool.query(
        `
        SELECT
          id,
          value,
          "songId",
          "createdAt",
          "updatedAt"
        FROM "Rating"
        WHERE "userId" = $1
        ORDER BY "songId"
        `,
        [req.userId],
      );

      return res.json({
        ratings: result.rows,
      });
    } catch (error) {
      console.error("Failed to fetch ratings:", error);

      return res.status(500).json({
        error: "Failed to fetch ratings",
      });
    }
  },
);

app.get(
  "/api/recommendations",
  requireAuth,
  async (req: AuthenticatedRequest, res) => {
    try {
      if (!req.userId) {
        return res.status(401).json({
          error: "Authentication required",
        });
      }

      const projectRoot = path.resolve(process.cwd(), "..");

      const pythonPath = path.join(
        projectRoot,
        "recommender",
        ".venv",
        "bin",
        "python",
      );

      const recommenderPath = path.join(
        projectRoot,
        "recommender",
        "src",
        "preprocessing",
        "recommend.py",
      );

      const { stdout } = await execFileAsync(
        pythonPath,
        [recommenderPath, String(req.userId)],
        {
          cwd: projectRoot,
        },
      );

      const data = JSON.parse(stdout.trim());

      return res.json(data);
    } catch (error) {
      console.error("Failed to generate recommendations:", error);

      return res.status(500).json({
        error: "Failed to generate recommendations",
      });
    }
  },
);

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
