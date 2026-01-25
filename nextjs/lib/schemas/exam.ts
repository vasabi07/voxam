import { z } from "zod"

export const examModeSchema = z.enum(["exam", "learn"])

export const difficultyLevelSchema = z.enum(["basic", "intermediate", "advanced"])

export const questionTypeSchema = z.enum([
  "multiple_choice",
  "long_answer",
  "short_answer",
  "true_false",
])

export const bloomLevelSchema = z.enum([
  "remember",
  "understand",
  "apply",
  "analyze",
  "evaluate",
  "create",
])

export const qpTypeSchema = z.enum(["regular", "midterm", "final", "quiz"])

export const createExamSchema = z.object({
  title: z.string().optional(),
  documentId: z.string().min(1, "Please select a document"),
  mode: examModeSchema.default("exam"),
  scheduling: z.enum(["now", "later"]).default("now"),
  duration: z.coerce
    .number()
    .min(5, "Duration must be at least 5 minutes")
    .max(180, "Duration cannot exceed 180 minutes")
    .default(60),
  numQuestions: z.coerce
    .number()
    .min(1, "At least 1 question required")
    .max(50, "Maximum 50 questions allowed")
    .default(10),
  difficultyLevels: z
    .array(difficultyLevelSchema)
    .min(1, "Select at least one difficulty level")
    .default(["basic", "intermediate", "advanced"]),
  questionTypes: z
    .array(questionTypeSchema)
    .min(1, "Select at least one question type")
    .default(["long_answer", "multiple_choice"]),
  bloomLevels: z
    .array(bloomLevelSchema)
    .min(1, "Select at least one Bloom's level")
    .default(["remember", "understand", "apply", "analyze", "evaluate"]),
  typeOfQp: qpTypeSchema.default("regular"),
})

export type ExamMode = z.infer<typeof examModeSchema>
export type DifficultyLevel = z.infer<typeof difficultyLevelSchema>
export type QuestionType = z.infer<typeof questionTypeSchema>
export type BloomLevel = z.infer<typeof bloomLevelSchema>
export type QpType = z.infer<typeof qpTypeSchema>
export type CreateExamInput = z.infer<typeof createExamSchema>
