import request from "supertest";
import { describe, expect, it } from "vitest";

import app from "../src/app";

// Basic authentication checks for the preferences endpoints.
// These tests do not need a real user/database setup because they
// verify that protected routes reject unauthenticated requests before
// the route handler reaches any database logic.
describe("Preferences API", () => {
  it("rejects requests without authentication", async () => {
    // Call protected endpoint without an Authorization header.
    const response = await request(app).get("/api/preferences");

    expect(response.status).toBe(401);
  });

  it("rejects requests with an invalid token", async () => {
    // Send a malformed/invalid Bearer token to confirm JWT validation fails.
    const response = await request(app)
      .get("/api/preferences")
      .set("Authorization", "Bearer definitely-not-a-valid-token");

    expect(response.status).toBe(401);
  });
});
