// Auth schemas
export {
  loginSchema,
  registerSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
  type LoginInput,
  type RegisterInput,
  type ForgotPasswordInput,
  type ResetPasswordInput,
} from "./auth"

// Exam schemas
export {
  examModeSchema,
  difficultyLevelSchema,
  questionTypeSchema,
  bloomLevelSchema,
  qpTypeSchema,
  createExamSchema,
  type ExamMode,
  type DifficultyLevel,
  type QuestionType,
  type BloomLevel,
  type QpType,
  type CreateExamInput,
} from "./exam"

// Document schemas
export {
  uploadDocumentSchema,
  qpFormSchema,
  learnPackFormSchema,
  type UploadDocumentInput,
  type QpFormInput,
  type LearnPackFormInput,
} from "./document"

// Payment schemas
export {
  regionSchema,
  planIdSchema,
  createOrderSchema,
  verifyPaymentSchema,
  type Region,
  type PlanId,
  type CreateOrderInput,
  type VerifyPaymentInput,
} from "./payment"
