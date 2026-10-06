import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import app from "../src/app";
import { pool } from "../src/db";

describe("Preferences API integration", () => {
  const testEmail = "api-test-user@example.com";
  const testUsername = "api_test_user";
  const testPassword = "TestPassword123!";

  let token = "";
  let userId = 0;
  let genreId = 0;
  let artistId = 0;

  beforeAll(async () => {
    // Clean up in case a previous failed run left the test user behind.
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

    const genreResult = await pool.query(
      `
      SELECT id
      FROM "Genre"
      ORDER BY id
      LIMIT 1
      `,
    );

    const artistResult = await pool.query(
      `
      SELECT id
      FROM "Artist"
      ORDER BY id
      LIMIT 1
      `,
    );

    expect(genreResult.rows.length).toBeGreaterThan(0);
    expect(artistResult.rows.length).toBeGreaterThan(0);

    genreId = genreResult.rows[0].id;
    artistId = artistResult.rows[0].id;
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

  it("saves preferences for an authenticated user", async () => {
    const response = await request(app)
      .put("/api/preferences")
      .set("Authorization", `Bearer ${token}`)
      .send({
        genreIds: [genreId],
        artistIds: [artistId],
      });

    expect(response.status).toBe(200);

    expect(response.body.genres).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: genreId,
        }),
      ]),
    );

    expect(response.body.artists).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: artistId,
        }),
      ]),
    );
  });

  it("loads the saved preferences back", async () => {
    const response = await request(app)
      .get("/api/preferences")
      .set("Authorization", `Bearer ${token}`);

    expect(response.status).toBe(200);

    expect(response.body.genres).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: genreId,
        }),
      ]),
    );

    expect(response.body.artists).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: artistId,
        }),
      ]),
    );
  });
});
