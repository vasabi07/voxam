"use client"

import { CopilotChat } from "@copilotkit/react-ui";

export default function ChatPage() {
  return (
    <div className="h-[calc(100vh-4rem)] w-full p-4">
      <CopilotChat
        className="h-full w-full"
        instructions={"You are a helpful academic tutor. Explain concepts clearly and patiently."}
        labels={{
          title: "Study Room",
          initial: "Welcome to the study room. What subject are we focusing on today?",
        }}
      />
    </div>
  );
}
