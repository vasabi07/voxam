"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { Loader2, CheckCircle2, BookOpen } from "lucide-react";
import { v4 as uuidv4 } from "uuid";

type TopicInfo = {
  name: string;
  chunk_count: number;
  pages: number[];
};

type LPStatus = "IDLE" | "LOADING_TOPICS" | "SELECTING" | "CREATING" | "READY";

interface LearnPackFormProps {
  docId: string
  isFromHistory?: boolean  // When true, render as read-only placeholder
}

export function LearnPackForm({ docId, isFromHistory }: LearnPackFormProps) {
  const [status, setStatus] = useState<LPStatus>("IDLE");
  const [availableTopics, setAvailableTopics] = useState<TopicInfo[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [sessionUrl, setSessionUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<{ id: string; filename: string }[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string>(docId);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Load user's documents if no docId provided
  useEffect(() => {
    // Skip loading for historical views
    if (isFromHistory) return;

    if (!docId) {
      loadDocuments();
    } else {
      loadTopics(docId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId, isFromHistory]);

  // Historical view - show disabled placeholder for messages from previous sessions
  if (isFromHistory) {
    return (
      <div className="p-4 bg-muted/50 rounded-lg border border-dashed border-gray-300 w-full max-w-md">
        <p className="text-sm text-muted-foreground">
          Learning session form was shown here
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Type &quot;learn&quot; or &quot;study&quot; to start a new learning session
        </p>
      </div>
    );
  }

  const loadDocuments = async () => {
    try {
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;

      const { data: docs } = await supabase
        .from("Document")
        .select("id, filename")
        .eq("userId", user.id)
        .eq("status", "READY")
        .order("createdAt", { ascending: false });

      if (docs && docs.length > 0) {
        setDocuments(docs);
        setStatus("IDLE");
      }
    } catch (e) {
      console.error("Failed to load documents:", e);
    }
  };

  const loadTopics = async (documentId: string) => {
    if (!documentId) return;

    setStatus("LOADING_TOPICS");
    setError(null);
    setSelectedDocId(documentId);

    try {
      // Get auth token for API call
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        setError("Not authenticated. Please log in again.");
        setStatus("IDLE");
        return;
      }

      const response = await fetch(`${apiUrl}/topics?doc_id=${documentId}`, {
        headers: {
          "Authorization": `Bearer ${session.access_token}`
        }
      });
      const data = await response.json();

      if (data.topics && data.topics.length > 0) {
        setAvailableTopics(data.topics);
        setStatus("SELECTING");
      } else {
        setError("No topics found in this document. Try a different document.");
        setStatus("IDLE");
      }
    } catch (e) {
      console.error("Failed to load topics:", e);
      setError("Failed to load topics. Please try again.");
      setStatus("IDLE");
    }
  };

  const toggleTopic = (topicName: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topicName)
        ? prev.filter((t) => t !== topicName)
        : [...prev, topicName]
    );
  };

  const selectAllTopics = () => {
    if (selectedTopics.length === availableTopics.length) {
      setSelectedTopics([]);
    } else {
      setSelectedTopics(availableTopics.map((t) => t.name));
    }
  };

  const startLearning = async () => {
    if (selectedTopics.length === 0) {
      toast.error("Please select at least one topic");
      return;
    }

    setStatus("CREATING");

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      if (!session?.access_token) {
        toast.error("You must be logged in");
        setStatus("SELECTING");
        return;
      }

      const lpId = `lp_${uuidv4().slice(0, 8)}`;
      const threadId = `learn_${uuidv4().slice(0, 8)}`;

      // 1. Create Learn Pack in Redis (user_id from JWT, not request body)
      const createLpResponse = await fetch(`${apiUrl}/create-lp`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          lp_id: lpId,
          doc_id: selectedDocId,
          // user_id removed - backend gets it from JWT
          topics: selectedTopics,
        }),
      });

      if (!createLpResponse.ok) {
        const errorData = await createLpResponse.json();
        throw new Error(errorData.detail || "Failed to create Learn Pack");
      }

      // 2. Get user's region preference
      let userRegion = "india";
      try {
        const regionResponse = await fetch("/api/user/region");
        if (regionResponse.ok) {
          const regionData = await regionResponse.json();
          userRegion = regionData.region || "india";
        }
      } catch (e) {
        console.warn("Could not fetch user region, using default:", e);
      }

      // 3. Start learn session (get LiveKit token)
      const sessionResponse = await fetch(`${apiUrl}/start-learn-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          lp_id: lpId,
          thread_id: threadId,
          region: userRegion,
        }),
      });

      const sessionData = await sessionResponse.json();

      if (!sessionData.success) {
        throw new Error(sessionData.error || "Failed to start session");
      }

      // 4. Build redirect URL
      const url = new URL("/authenticated/learn", window.location.origin);
      url.searchParams.set("room", sessionData.room_name);
      url.searchParams.set("token", sessionData.token);
      url.searchParams.set("url", sessionData.livekit_url);
      url.searchParams.set("lp_id", lpId);
      url.searchParams.set("thread_id", threadId);

      setSessionUrl(url.toString());
      setStatus("READY");

    } catch (e) {
      console.error("Failed to start learning session:", e);
      toast.error(e instanceof Error ? e.message : "Failed to create learn session");
      setStatus("SELECTING");
    }
  };

  // Ready state - show success + start button
  if (status === "READY" && sessionUrl) {
    return (
      <div className="p-6 bg-emerald-50 rounded-xl border border-emerald-100 flex flex-col items-center text-center gap-3 shadow-sm animate-in fade-in zoom-in">
        <div className="h-12 w-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center">
          <CheckCircle2 size={24} />
        </div>
        <h3 className="text-lg font-bold text-gray-800">Ready to Learn!</h3>
        <p className="text-sm text-gray-600">
          {selectedTopics.length} topic{selectedTopics.length > 1 ? "s" : ""} selected
        </p>
        <button
          onClick={() => (window.location.href = sessionUrl)}
          className="mt-2 w-full bg-emerald-600 text-white py-2 rounded-lg font-medium hover:bg-emerald-700 transition-colors"
        >
          Start Learning Session
        </button>
      </div>
    );
  }

  // Form state
  return (
    <div className="p-5 bg-[#FAF9F6] rounded-xl border border-gray-200 shadow-sm w-full max-w-md">
      <h3 className="text-lg font-bold text-[#374151] mb-4 flex items-center gap-2">
        <BookOpen className="h-5 w-5 text-emerald-600" />
        Select Topics to Study
      </h3>

      {error && (
        <div className="mb-4 p-2 bg-red-50 text-red-600 text-sm rounded">{error}</div>
      )}

      {/* Document selector (if no docId provided) */}
      {!docId && status === "IDLE" && documents.length > 0 && (
        <div className="space-y-3 mb-4">
          <label className="text-sm font-medium text-gray-600">Select a document</label>
          <div className="space-y-2 max-h-[200px] overflow-y-auto">
            {documents.map((doc) => (
              <div
                key={doc.id}
                onClick={() => loadTopics(doc.id)}
                className="flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors border-gray-200 hover:bg-gray-50"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{doc.filename}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {status === "LOADING_TOPICS" && (
        <div className="flex items-center gap-2 py-8 justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />
          <span>Loading topics...</span>
        </div>
      )}

      {status === "SELECTING" && (
        <>
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm text-gray-500">
              {availableTopics.length} topics available
            </span>
            <button
              type="button"
              onClick={selectAllTopics}
              className="text-sm text-emerald-600 hover:text-emerald-700 font-medium"
            >
              {selectedTopics.length === availableTopics.length
                ? "Deselect All"
                : "Select All"}
            </button>
          </div>

          <div className="space-y-2 max-h-[300px] overflow-y-auto mb-4">
            {availableTopics.map((topic) => (
              <div
                key={topic.name}
                onClick={() => toggleTopic(topic.name)}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedTopics.includes(topic.name)
                    ? "border-emerald-500 bg-emerald-500/10"
                    : "border-gray-200 hover:bg-gray-50"
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedTopics.includes(topic.name)}
                  onChange={() => {}}
                  className="h-4 w-4 accent-emerald-600 pointer-events-none"
                />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{topic.name}</p>
                  <p className="text-xs text-gray-500">
                    {topic.chunk_count} section{topic.chunk_count > 1 ? "s" : ""}
                    {topic.pages.length > 0 && ` • Pages ${topic.pages.slice(0, 3).join(", ")}${topic.pages.length > 3 ? "..." : ""}`}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={startLearning}
            disabled={selectedTopics.length === 0}
            className="w-full bg-emerald-600 text-white py-2.5 rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Start Learning ({selectedTopics.length} selected)
          </button>
        </>
      )}

      {status === "CREATING" && (
        <div className="flex items-center gap-2 py-8 justify-center">
          <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />
          <span>Creating learn session...</span>
        </div>
      )}

      {status === "IDLE" && !docId && documents.length === 0 && (
        <div className="py-8 text-center text-gray-500">
          <p className="text-sm">No documents found.</p>
          <p className="text-xs mt-1">Upload a document first to start learning.</p>
        </div>
      )}
    </div>
  );
}
