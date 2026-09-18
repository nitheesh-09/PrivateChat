"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { User, Message, WSEvent } from "@/lib/types";
import { WS_BASE_URL } from "@/lib/api";

interface UseChatSocketProps {
  user: User | null;
  onNewMessage: (conversationId: string, message: Message) => void;
  onMessagesRead: (conversationId: string, messageIds: string[], readAt: string) => void;
  onUserStatus: (userId: string, username: string, isOnline: boolean, lastSeen: string) => void;
  onTyping: (conversationId: string, userId: string, username: string, isTyping: boolean) => void;
}

export function useChatSocket({
  user,
  onNewMessage,
  onMessagesRead,
  onUserStatus,
  onTyping,
}: UseChatSocketProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const isMountedRef = useRef(true);

  const callbacksRef = useRef({
    onNewMessage,
    onMessagesRead,
    onUserStatus,
    onTyping,
  });

  useEffect(() => {
    callbacksRef.current = {
      onNewMessage,
      onMessagesRead,
      onUserStatus,
      onTyping,
    };
  }, [onNewMessage, onMessagesRead, onUserStatus, onTyping]);

  const connect = useCallback(() => {
    if (!user || socketRef.current) return;

    try {
      const ws = new WebSocket(WS_BASE_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        if (!isMountedRef.current) return;
        setIsConnected(true);
        setIsReconnecting(false);
        reconnectAttemptRef.current = 0;

        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, 25000);
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;
        try {
          const data: WSEvent = JSON.parse(event.data);

          switch (data.type) {
            case "new_message":
              callbacksRef.current.onNewMessage(data.conversation_id, data.message);
              break;
            case "messages_read":
              callbacksRef.current.onMessagesRead(data.conversation_id, data.message_ids, data.read_at);
              break;
            case "user_status":
              callbacksRef.current.onUserStatus(data.user_id, data.username, data.is_online, data.last_seen);
              break;
            case "typing":
              callbacksRef.current.onTyping(data.conversation_id, data.user_id, data.username, data.is_typing);
              break;
            case "pong":
              break;
            case "error":
              console.warn("WebSocket message error:", data.message);
              break;
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.onclose = (event) => {
        if (!isMountedRef.current) return;
        setIsConnected(false);
        socketRef.current = null;

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        if (event.code !== 1000 && event.code !== 1008 && user) {
          setIsReconnecting(true);
          const backoff = Math.min(1000 * Math.pow(1.5, reconnectAttemptRef.current), 10000);
          reconnectAttemptRef.current += 1;

          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMountedRef.current) connect();
          }, backoff);
        }
      };

      ws.onerror = (err) => {
        console.warn("WebSocket error:", err);
        ws.close();
      };
    } catch (err) {
      console.error("WebSocket connection initiation error:", err);
    }
  }, [user]);

  useEffect(() => {
    isMountedRef.current = true;
    if (user) {
      connect();
    }

    return () => {
      isMountedRef.current = false;
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        socketRef.current.close(1000);
        socketRef.current = null;
      }
    };
  }, [user, connect]);

  const sendMessage = useCallback((conversationId: string, content: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "send_message",
          conversation_id: conversationId,
          content,
        })
      );
      return true;
    }
    return false;
  }, []);

  const markRead = useCallback((conversationId: string, messageIds: string[]) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN && messageIds.length > 0) {
      socketRef.current.send(
        JSON.stringify({
          type: "mark_read",
          conversation_id: conversationId,
          message_ids: messageIds,
        })
      );
    }
  }, []);

  const sendTyping = useCallback((conversationId: string, isTyping: boolean) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: "typing",
          conversation_id: conversationId,
          is_typing: isTyping,
        })
      );
    }
  }, []);

  return {
    isConnected,
    isReconnecting,
    sendMessage,
    markRead,
    sendTyping,
  };
}
