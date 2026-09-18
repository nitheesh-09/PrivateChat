import { AuthResponse, Conversation, Message, User } from "./types";

function resolveApiBase(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (envUrl && envUrl.trim()) {
    let clean = envUrl.trim().replace(/\/+$/, "");
    if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
      clean = `https://${clean}`;
    }
    // Automatically redirect outdated/generic Render URL to the user's active backend
    if (clean === "https://privatechat-backend.onrender.com") {
      return "https://privatechat-backend-7it3.onrender.com";
    }
    return clean;
  }

  // Auto-detect production Render deployment in browser
  if (typeof window !== "undefined" && window.location.hostname.includes("onrender.com")) {
    return "https://privatechat-backend-7it3.onrender.com";
  }

  return "http://localhost:8000";
}

function resolveWsBase(apiBase: string): string {
  const envWs = process.env.NEXT_PUBLIC_WS_URL;
  if (envWs && envWs.trim()) {
    let clean = envWs.trim().replace(/\/+$/, "");
    if (!clean.startsWith("ws://") && !clean.startsWith("wss://")) {
      clean = `wss://${clean}`;
    }
    if (clean === "wss://privatechat-backend.onrender.com/ws/chat") {
      return "wss://privatechat-backend-7it3.onrender.com/ws/chat";
    }
    return clean;
  }
  if (apiBase.startsWith("https://")) {
    return apiBase.replace("https://", "wss://") + "/ws/chat";
  }
  return apiBase.replace("http://", "ws://") + "/ws/chat";
}

export const API_BASE_URL = resolveApiBase();
export const WS_BASE_URL = resolveWsBase(API_BASE_URL);

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    cache: "no-store", // Crucial: prevent browser and Next.js client caching
    ...options,
    headers,
    credentials: "include", // Sends and receives HttpOnly cookies
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const data = await response.json();
      if (data.detail) {
        errorDetail = data.detail;
      } else if (data.message) {
        errorDetail = data.message;
      }
    } catch {
      // Body not json
    }
    throw new ApiError(errorDetail, response.status);
  }

  return response.json();
}

export const api = {
  // Auth
  register: (username: string, password: string) =>
    request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  login: (username: string, password: string) =>
    request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  logout: () =>
    request<{ message: string }>("/api/auth/logout", {
      method: "POST",
    }),

  getMe: () => request<AuthResponse>("/api/auth/me"),

  // Users Directory
  getUsers: () => request<User[]>("/api/users"),

  searchUsers: (query: string) =>
    request<User[]>(`/api/users/search?q=${encodeURIComponent(query)}`),

  // Conversations
  getConversations: () => request<Conversation[]>("/api/conversations"),

  createDirectConversation: (userId: string) =>
    request<Conversation>("/api/conversations/direct", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),

  createGroupConversation: (name: string, memberIds: string[]) =>
    request<Conversation>("/api/conversations/group", {
      method: "POST",
      body: JSON.stringify({ name, member_ids: memberIds }),
    }),

  getConversationDetails: (conversationId: string) =>
    request<Conversation>(`/api/conversations/${conversationId}`),

  getConversationMessages: (conversationId: string, limit = 100, offset = 0) =>
    request<Message[]>(`/api/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`),

  sendConversationMessage: (conversationId: string, content: string) =>
    request<Message>(`/api/conversations/${conversationId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  markConversationRead: (conversationId: string, messageIds?: string[]) =>
    request<{ read_count: number; message_ids: string[] }>(`/api/conversations/${conversationId}/read`, {
      method: "POST",
      body: JSON.stringify({ message_ids: messageIds || [] }),
    }),

  addGroupMembers: (conversationId: string, memberIds: string[]) =>
    request<Conversation>(`/api/conversations/${conversationId}/members`, {
      method: "POST",
      body: JSON.stringify({ member_ids: memberIds }),
    }),
};
