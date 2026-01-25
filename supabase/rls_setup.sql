-- ============================================================
-- Voxam RLS Policies ONLY (Realtime already enabled)
-- Run this in: Supabase Dashboard → SQL Editor
-- ============================================================

-- USER policies
CREATE POLICY "user_select_own" ON "User"
  FOR SELECT USING ((select auth.uid())::text = id);

CREATE POLICY "user_update_own" ON "User"
  FOR UPDATE USING ((select auth.uid())::text = id);

-- DOCUMENT policies
CREATE POLICY "document_select_own" ON "Document"
  FOR SELECT USING ((select auth.uid())::text = "userId");

CREATE POLICY "document_insert_own" ON "Document"
  FOR INSERT WITH CHECK ((select auth.uid())::text = "userId");

CREATE POLICY "document_update_own" ON "Document"
  FOR UPDATE USING ((select auth.uid())::text = "userId");

CREATE POLICY "document_delete_own" ON "Document"
  FOR DELETE USING ((select auth.uid())::text = "userId");

-- EXAM SESSION policies
CREATE POLICY "session_select_own" ON "ExamSession"
  FOR SELECT USING ((select auth.uid())::text = "userId");

CREATE POLICY "session_insert_own" ON "ExamSession"
  FOR INSERT WITH CHECK ((select auth.uid())::text = "userId");

CREATE POLICY "session_update_own" ON "ExamSession"
  FOR UPDATE USING ((select auth.uid())::text = "userId");

-- CORRECTION REPORT policies
CREATE POLICY "report_select_own" ON "CorrectionReport"
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM "ExamSession"
      WHERE "ExamSession".id = "CorrectionReport"."examSessionId"
      AND "ExamSession"."userId" = (select auth.uid())::text
    )
  );

-- TRANSACTION policies
CREATE POLICY "transaction_select_own" ON "Transaction"
  FOR SELECT USING ((select auth.uid())::text = "userId");

-- SUBSCRIPTION PLAN policies (public read)
CREATE POLICY "plan_select_public" ON "SubscriptionPlan"
  FOR SELECT USING (true);
