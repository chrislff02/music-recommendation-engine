import request from "supertest";
import { describe, expect, it } from "vitest";

import app from "../src/app";

describe("Preferences API", () => {
  it("rejects requests without authentication", async () => {
    const response = await request(app).get("/api/preferences");

    expect(response.status).toBe(401);
  });
});

it("rejects requests with an invalid token", async () => {
  const response = await request(app)
    .get("/api/preferences")
    .set("Authorization", "Bearer definitely-not-a-valid-token");

  expect(response.status).toBe(401);
});
