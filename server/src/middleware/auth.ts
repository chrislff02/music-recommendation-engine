import type { NextFunction, Request, Response } from "express";
import jwt from "jsonwebtoken";

type JwtPayload = {
  userId: number;
};

export type AuthenticatedRequest = Request & {
  userId?: number;
};

export function requireAuth(
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction,
) {
  const authHeader = req.headers.authorization;

  if (!authHeader?.startsWith("Bearer ")) {
    return res.status(401).json({
      error: "Authentication required",
    });
  }

  const token = authHeader.split(" ")[1];

  const jwtSecret = process.env.JWT_SECRET;

  if (!jwtSecret) {
    throw new Error("JWT_SECRET is not defined");
  }

  try {
    const payload = jwt.verify(token, jwtSecret) as JwtPayload;

    req.userId = payload.userId;

    return next();
  } catch {
    return res.status(401).json({
      error: "Invalid or expired token",
    });
  }
}
