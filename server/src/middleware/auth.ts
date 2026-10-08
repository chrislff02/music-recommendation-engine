import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";

// Shape of the data stored inside MusicMatch JWT access tokens.
type JwtPayload = {
  userId: number;
};

// Extends the normal Express request so authenticated routes can
// access the user ID added by the authentication middleware.
export type AuthenticatedRequest = Request & {
  userId?: number;
};

// Protect routes that require a logged-in user.
// The middleware expects an Authorization header in the form:
// Bearer <token>
// If the token is valid, the decoded user ID is attached to the
// request before passing control to the protected route.
export function requireAuth(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
) {
  const authHeader = req.headers.authorization;

  // Reject requests that do not include a Bearer token.
  if (!authHeader?.startsWith("Bearer ")) {
    return res.status(401).json({
      error: "Authentication required",
    });
  }

  // Extract the token portion from "Bearer <token>".
  const token = authHeader.split(" ")[1];

  const jwtSecret = process.env.JWT_SECRET;

  // JWT verification cannot run without the server secret.
  if (!jwtSecret) {
    throw new Error("JWT_SECRET is not defined");
  }

  try {
    // Verify the token signature & expiration, then read the
    // authenticated user's ID from the token payload.
    const payload = jwt.verify(token, jwtSecret) as JwtPayload;

    req.userId = payload.userId;

    // Continue to the protected route.
    return next();
  } catch {
    // Invalid/tampered/expired tokens are treated as unauthorized.
    return res.status(401).json({
      error: "Invalid or expired token",
    });
  }
}
