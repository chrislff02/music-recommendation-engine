import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import app from "../src/app";
import { pool } from "../src/db";

// Integration tests for creating & updating song ratings
// against the real PostgreSQL database.
describe("Ratings API integration", () => {
  // Dedicated test account values keep this suite isolated from normal users.
  const testEmail = "rating-api-test@example.com";
  const testUsername = "rating_api_test_user";
  const testPassword = "TestPassword123!";

  // Values created/discovered during setup & reused by the tests.
  let token = "";
  let userId = 0;
  let songId = 0;

  beforeAll(async () => {
    // Clean up in case a previous failed test run left this user behind.
    await pool.query(
      `
      DELETE FROM "User"
      WHERE email = $1 OR username = $2
      `,
      [testEmail, testUsername],
    );

    // Register a fresh user through the real API so the test receives
    // a valid JWT token for protected rating routes.
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

    // Reuse an existing song from the catalog for the rating tests.
    const songResult = await pool.query(
      `
      SELECT id
      FROM "Song"
      ORDER BY id
      LIMIT 1
      `,
    );

    // The integration test requires at least one song in the catalog.
    expect(songResult.rows.length).toBeGreaterThan(0);

    songId = songResult.rows[0].id;
  });

  afterAll(async () => {
    // Remove the temporary test user after the suite finishes.
    // Related ratings are removed through the database relations.
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
    // Save an initial 4-star rating for the selected song.
    const response = await request(app)
      .post("/api/ratings")
      .set("Authorization", `Bearer ${token}`)
      .send({
        songId,
        value: 4,
      });

    expect(response.status).toBe(200);

    // Confirm the API returns the rating tied to the correct user & song.
    expect(response.body.rating).toEqual(
      expect.objectContaining({
        userId,
        songId,
        value: 4,
      }),
    );
  });

  it("updates an existing rating instead of creating a duplicate", async () => {
    // Submit a second rating for the same user/song pair.
    // The API should update the existing row through its upsert logic.
    const response = await request(app)
      .post("/api/ratings")
      .set("Authorization", `Bearer ${token}`)
      .send({
        songId,
        value: 2,
      });

    expect(response.status).toBe(200);

    // Confirm the returned rating now contains the updated value.
    expect(response.body.rating).toEqual(
      expect.objectContaining({
        userId,
        songId,
        value: 2,
      }),
    );

    // Query PostgreSQL directly to verify that only one rating row exists
    // for this user/song pair after the update.
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
