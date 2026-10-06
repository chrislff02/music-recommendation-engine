import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import app from "../src/app";
import { pool } from "../src/db";

describe("Ratings API integration", () => {
  const testEmail = "rating-api-test@example.com";
  const testUsername = "rating_api_test_user";
  const testPassword = "TestPassword123!";

  let token = "";
  let userId = 0;
  let songId = 0;

  beforeAll(async () => {
    await pool.query(
      `
      DELETE FROM "User"
      WHERE email = $1 OR username = $2
      `,
      [testEmail, testUsername],
    );

    const registerResponse = await request(app)
      .post("/api/auth/register")
      .send({
        email: testEmail,
        username: testUsername,
        password: testPassword,
      });

    expect(registerResponse.status).toBe(201);

    token = registerResponse.body.token;
    userId = registerResponse.body.user.id;

    const songResult = await pool.query(
      `
      SELECT id
      FROM "Song"
      ORDER BY id
      LIMIT 1
      `,
    );

    expect(songResult.rows.length).toBeGreaterThan(0);

    songId = songResult.rows[0].id;
  });

  afterAll(async () => {
    if (userId) {
      await pool.query(
        `
        DELETE FROM "User"
        WHERE id = $1
        `,
        [userId],
      );
    }
  });

  it("creates a rating for an authenticated user", async () => {
    const response = await request(app)
      .post("/api/ratings")
      .set("Authorization", `Bearer ${token}`)
      .send({
        songId,
        value: 4,
      });

    expect(response.status).toBe(200);

    expect(response.body.rating).toEqual(
      expect.objectContaining({
        userId,
        songId,
        value: 4,
      }),
    );
  });

  it("updates an existing rating instead of creating a duplicate", async () => {
    const response = await request(app)
      .post("/api/ratings")
      .set("Authorization", `Bearer ${token}`)
      .send({
        songId,
        value: 2,
      });

    expect(response.status).toBe(200);

    expect(response.body.rating).toEqual(
      expect.objectContaining({
        userId,
        songId,
        value: 2,
      }),
    );

    const databaseResult = await pool.query(
      `
      SELECT id, value
      FROM "Rating"
      WHERE "userId" = $1
        AND "songId" = $2
      `,
      [userId, songId],
    );

    expect(databaseResult.rows).toHaveLength(1);
    expect(databaseResult.rows[0].value).toBe(2);
  });
});
