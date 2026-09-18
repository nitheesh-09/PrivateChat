export interface User {
  id: string;
  username: string;
  created_at: string;
  last_seen: string;
  is_online: boolean;
}

export type MessageStatus = "sent" | "delivered" | "read";

export interface Message {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_username: string;
  content: string;
  created_at: string;
  delivered_at?: string | null;
  read_at?: string | null;
  status: MessageStatus;
}

export interface Member {
  id: string;
  username: string;
  is_online: boolean;
  last_seen: string;
  joined_at: string;
}

export interface Conversation {
  id: string;
  type: "direct" | "group";
  name?: string | null;
  display_name: string;
  created_at: string;
  created_by?: string | null;
  members: Member[];
  last_message?: Message | null;
  unread_count: number;
}

export interface AuthResponse {
  user: User;
  message: string;
}

export type WSEvent =
  | { type: "new_message"; conversation_id: string; message: Message }
  | { type: "conversation_created"; conversation_id: string }
  | { type: "messages_read"; conversation_id: string; message_ids: string[]; read_at: string }
  | { type: "user_status"; user_id: string; username: string; is_online: boolean; last_seen: string }
  | { type: "typing"; conversation_id: string; user_id: string; username: string; is_typing: boolean }
  | { type: "pong" }
  | { type: "error"; message: string };
