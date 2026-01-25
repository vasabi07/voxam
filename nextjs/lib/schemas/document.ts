import { z } from "zod"

const MAX_FILE_SIZE = 50 * 1024 * 1024 // 50MB
const ACCEPTED_FILE_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

export const uploadDocumentSchema = z.object({
  file: z
    .instanceof(File, { message: "Please select a file" })
    .refine((file) => file.size <= MAX_FILE_SIZE, "File size must be less than 50MB")
    .refine(
      (file) => ACCEPTED_FILE_TYPES.includes(file.type),
      "Only PDF and DOCX files are accepted"
    ),
  title: z.string().optional(),
})

export const qpFormSchema = z.object({
  docId: z.string().min(1, "Document ID is required"),
  numQuestions: z.coerce
    .number()
    .min(1, "At least 1 question required")
    .max(50, "Maximum 50 questions")
    .default(10),
  duration: z.coerce
    .number()
    .min(5, "Duration must be at least 5 minutes")
    .max(180, "Maximum 180 minutes")
    .default(60),
  difficulty: z
    .array(z.enum(["basic", "intermediate", "advanced"]))
    .min(1, "Select at least one difficulty")
    .default(["basic", "intermediate", "advanced"]),
})

export const learnPackFormSchema = z.object({
  docId: z.string().min(1, "Document ID is required"),
  numTopics: z.coerce
    .number()
    .min(1, "At least 1 topic required")
    .max(20, "Maximum 20 topics")
    .default(5),
  focusAreas: z.string().optional(),
})

export type UploadDocumentInput = z.infer<typeof uploadDocumentSchema>
export type QpFormInput = z.infer<typeof qpFormSchema>
export type LearnPackFormInput = z.infer<typeof learnPackFormSchema>
