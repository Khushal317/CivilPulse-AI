import { z } from "zod";

const acceptedTypes = ["image/jpeg", "image/png", "image/webp"];
const maxImageBytes = 10 * 1024 * 1024;

export const reportSchema = z
  .object({
    image: z
      .custom<FileList>((value) => value instanceof FileList, "Choose an issue photo.")
      .refine((files) => files.length === 1, "Choose one issue photo.")
      .refine(
        (files) => files.item(0)?.size !== undefined && files.item(0)!.size <= maxImageBytes,
        "The image must be smaller than 10 MB.",
      )
      .refine(
        (files) => acceptedTypes.includes(files.item(0)?.type ?? ""),
        "Choose a JPEG, PNG, or WebP image.",
      ),
    originalDescription: z
      .string()
      .trim()
      .min(10, "Describe the issue in at least 10 characters.")
      .max(4_000, "Keep the description under 4,000 characters."),
    location: z
      .string()
      .trim()
      .min(2, "Enter the area or location.")
      .max(255, "Keep the location under 255 characters."),
    latitude: z.number().min(-90).max(90).nullable(),
    longitude: z.number().min(-180).max(180).nullable(),
    landmark: z.string().trim().max(255),
    preferredCategory: z.enum([
      "",
      "road_damage",
      "garbage_waste",
      "streetlight",
      "water_leakage",
      "drainage_sewage",
      "public_safety",
      "other",
    ]),
    urgencyNote: z.string().trim().max(1_000),
    citizenName: z.string().trim().max(120),
    citizenContact: z.string().trim().max(255),
  })
  .superRefine((values, context) => {
    if ((values.latitude === null) !== (values.longitude === null)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Choose a complete location suggestion or enter the location manually.",
        path: ["location"],
      });
    }
  });
