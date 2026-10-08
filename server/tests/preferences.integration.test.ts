import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import app from "../src/app";
import { pool } from "../src/db";

// Integration tests for saving & loading a user's taste-profile
// preferences against the real PostgreSQL database.
describe("Preferences API integration", () => {
  // Dedicated test account values keep this test isolated from normal users.
  const testEmail = "api-test-user@example.com";
  const testUsername = "api_test_user";
  const testPassword = "TestPassword123!";

  // Values created/discovered during setup & reused by the tests.
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

    // Register a fresh user through the real API so the test also gets
    // a valid JWT token for the protected preferences routes.
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

    // Use existing catalog data instead of creating temporary genres/artists.
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

    // The integration test requires at least one genre & artist
    // to already exist in the catalog.
    expect(genreResult.rows.length).toBeGreaterThan(0);
    expect(artistResult.rows.length).toBeGreaterThan(0);

    genreId = genreResult.rows[0].id;
    artistId = artistResult.rows[0].id;
  });

  afterAll(async () => {
    // Remove the temporary test user after the suite finishes.
    // Related preference rows are removed through database relations.
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
    // Store one genre & one artist as the user's taste preferences.
    const response = await request(app)
      .put("/api/preferences")
      .set("Authorization", `Bearer ${token}`)
      .send({
        genreIds: [genreId],
        artistIds: [artistId],
      });

    expect(response.status).toBe(200);

    // Confirm the saved genre is returned by the API.
    expect(response.body.genres).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: genreId,
        }),
      ]),
    );

    // Confirm the saved artist is returned by the API.
    expect(response.body.artists).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: artistId,
        }),
      ]),
    );
  });

  it("loads the saved preferences back", async () => {
    // Fetch the authenticated user's saved taste profile.
    const response = await request(app)
      .get("/api/preferences")
      .set("Authorization", `Bearer ${token}`);

    expect(response.status).toBe(200);

    // Verify that the previously saved genre persisted in PostgreSQL.
    expect(response.body.genres).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: genreId,
        }),
      ]),
    );

    // Verify that the previously saved artist persisted in PostgreSQL.
    expect(response.body.artists).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: artistId,
        }),
      ]),
    );
  });
});
