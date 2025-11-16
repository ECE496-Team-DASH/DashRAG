import { QueryMode } from "@/types";
import type { NextApiRequest, NextApiResponse } from "next";

const API_BASE_URL = process.env.NEXT_PUBLIC_DASHRAG_API_URL || "http://localhost:8000";

const handler = async (req: NextApiRequest, res: NextApiResponse) => {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const { sessionId, content, mode } = req.body as {
      sessionId: string;
      content: string;
      mode: QueryMode;
    };

    if (!sessionId || !content) {
      return res.status(400).json({ error: "Missing sessionId or content" });
    }

    // Call DashRAG API (returns 202 with message_id, processes async)
    const postResponse = await fetch(`${API_BASE_URL}/messages?sid=${sessionId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content, mode: mode || "local" }),
    });

    if (!postResponse.ok) {
      const error = await postResponse.text();
      return res.status(postResponse.status).json({ error });
    }

    const postData = await postResponse.json();
    const messageId = postData.message_id;
    
    // Poll GET /messages until assistant response appears
    const maxAttempts = 60; // 60 seconds max
    const pollInterval = 1000; // 1 second
    
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      await new Promise(resolve => setTimeout(resolve, pollInterval));
      
      const getResponse = await fetch(`${API_BASE_URL}/messages?sid=${sessionId}`);
      if (!getResponse.ok) {
        continue; // Retry on error
      }
      
      const messages = await getResponse.json();
      
      // Find the assistant message that follows our user message
      const userMsgIndex = messages.findIndex((m: any) => m.id === messageId);
      if (userMsgIndex >= 0 && userMsgIndex < messages.length - 1) {
        const assistantMsg = messages[userMsgIndex + 1];
        if (assistantMsg && assistantMsg.role === "assistant") {
          // Found the response!
          return res.status(200).json({ message: assistantMsg });
        }
      }
    }
    
    // Timeout
    return res.status(504).json({ error: "Query timed out after 60 seconds" });
  } catch (error) {
    console.error("Chat API error:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
};

export default handler;
