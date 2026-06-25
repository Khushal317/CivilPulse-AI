import { z } from "zod";

export const reviewSchema = z.object({
  title: z.string().trim().min(5).max(180),
  original_description: z.string().trim().min(10).max(4_000),
  ai_summary: z.string().trim().min(20).max(4_000),
  category: z.enum([
    "road_damage",
    "garbage_waste",
    "streetlight",
    "water_leakage",
    "drainage_sewage",
    "public_safety",
    "other",
  ]),
  severity: z.enum(["low", "medium", "high", "critical"]),
  urgency_level: z.enum(["routine", "soon", "urgent", "immediate"]),
  urgency_reason: z.string().trim().min(10).max(2_000),
  suggested_department: z.string().trim().min(2).max(180),
  safety_risk: z.string().trim().min(5).max(2_000),
  citizen_explanation: z.string().trim().min(5).max(2_000),
  suggested_next_action: z.string().trim().min(5).max(2_000),
  location: z.string().trim().min(2).max(255),
  landmark: z.string().trim().max(255),
});

