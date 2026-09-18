"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Conversation, Message } from "@/lib/types";
import { useChatSocket } from "@/hooks/useChatSocket";
import { ChatHeader } from "@/components/ChatHeader";
import { ChatSidebar } from "@/components/ChatSidebar";
import { MessageList } from "@/components/MessageList";
import { MessageInput } from "@/components/MessageInput";

export default function ChatPage() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [typingMap, setTypingMap] = useState<
    Record<string, { username: string; isTyping: boolean }>
  >({});

  // Auth guard
  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  // Load user conversations
  const loadConversations = useCallback(async (selectFirst = false) => {
    try {
      setLoadingConversations(true);
      const list = await api.getConversations();
      setConversations(list);

      if (selectFirst && list.length > 0 && !activeConversationId) {
        setActiveConversationId(list[0].id);
      }
    } catch (err) {
      console.error("Failed to load conversations:", err);
    } finally {
      setLoadingConversations(false);
    }
  }, [activeConversationId]);

  useEffect(() => {
    if (user) {
      loadConversations(true);
    }
  }, [user, loadConversations]);

  // Active conversation object
  const activeConversation = useMemo(() => {
    return conversations.find((c) => c.id === activeConversationId) || null;
  }, [conversations, activeConversationId]);

  // Fetch messages when active conversation changes
  const loadActiveMessages = useCallback(async (convId: string) => {
    try {
      setLoadingMessages(true);
      const msgs = await api.getConversationMessages(convId);
      setMessages(msgs);

      // Mark unread messages as read
      await api.markConversationRead(convId);
      // Clear unread badge in sidebar
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, unread_count: 0 } : c))
      );
    } catch (err) {
      console.error("Failed to load messages for conversation:", err);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    if (activeConversationId) {
      loadActiveMessages(activeConversationId);
    } else {
      setMessages([]);
    }
  }, [activeConversationId, loadActiveMessages]);

  // Select conversation handler
  const handleSelectConversation = (convId: string) => {
    if (convId !== activeConversationId) {
      setActiveConversationId(convId);
    }
  };

  // Start Direct Chat handler
  const handleStartDirectChat = async (userId: string) => {
    const conv = await api.createDirectConversation(userId);
    await loadConversations();
    setActiveConversationId(conv.id);
  };

  // Create Group Chat handler
  const handleCreateGroupChat = async (name: string, memberIds: string[]) => {
    const conv = await api.createGroupConversation(name, memberIds);
    await loadConversations();
    setActiveConversationId(conv.id);
  };

  // WebSocket callbacks
  const handleNewMessage = useCallback(
    (conversationId: string, message: Message) => {
      // 1. If currently viewing this conversation, append message and mark as read
      if (conversationId === activeConversationId) {
        setMessages((prev) => {
          if (prev.some((m) => m.id === message.id)) {
            return prev.map((m) => (m.id === message.id ? message : m));
          }
          return [...prev, message];
        });

        if (user && message.sender_id !== user.id) {
          api.markConversationRead(conversationId, [message.id]).catch(() => {});
        }
      }

      // 2. Update conversation preview in sidebar
      setConversations((prev) => {
        const next = prev.map((c) => {
          if (c.id === conversationId) {
            const isMe = user && message.sender_id === user.id;
            const isCurrentlyActive = conversationId === activeConversationId;
            const newUnread = !isMe && !isCurrentlyActive ? c.unread_count + 1 : c.unread_count;

            return {
              ...c,
              last_message: message,
              unread_count: newUnread,
            };
          }
          return c;
        });

        // Re-sort conversations so active/latest moves to top
        next.sort((a, b) => {
          const timeA = a.last_message ? new Date(a.last_message.created_at).getTime() : new Date(a.created_at).getTime();
          const timeB = b.last_message ? new Date(b.last_message.created_at).getTime() : new Date(b.created_at).getTime();
          return timeB - timeA;
        });

        return next;
      });
    },
    [activeConversationId, user]
  );

  const handleMessagesRead = useCallback(
    (conversationId: string, messageIds: string[], readAt: string) => {
      if (conversationId === activeConversationId) {
        const idSet = new Set(messageIds);
        setMessages((prev) =>
          prev.map((m) => {
            if (idSet.has(m.id)) {
              return {
                ...m,
                read_at: readAt,
                status: "read",
              };
            }
            return m;
          })
        );
      }
    },
    [activeConversationId]
  );

  const handleUserStatus = useCallback(
    (userId: string, username: string, isOnline: boolean, lastSeen: string) => {
      setConversations((prev) =>
        prev.map((c) => ({
          ...c,
          members: c.members.map((m) =>
            m.id === userId ? { ...m, is_online: isOnline, last_seen: lastSeen } : m
          ),
        }))
      );
    },
    []
  );

  const handleTyping = useCallback(
    (conversationId: string, userId: string, username: string, isTyping: boolean) => {
      setTypingMap((prev) => ({
        ...prev,
        [conversationId]: { username, isTyping },
      }));

      if (isTyping) {
        setTimeout(() => {
          setTypingMap((prev) => ({
            ...prev,
            [conversationId]: { username, isTyping: false },
          }));
        }, 3000);
      }
    },
    []
  );

  // Initialize WebSocket connection
  const { isConnected, isReconnecting, sendMessage, sendTyping } = useChatSocket({
    user,
    onNewMessage: handleNewMessage,
    onMessagesRead: handleMessagesRead,
    onUserStatus: handleUserStatus,
    onTyping: handleTyping,
  });

  const handleSendMessage = async (content: string) => {
    if (!activeConversationId) return;

    // Try sending over WebSocket first
    const sent = sendMessage(activeConversationId, content);
    if (!sent) {
      // Fallback to REST API
      try {
        const newMsg = await api.sendConversationMessage(activeConversationId, content);
        setMessages((prev) => {
          if (prev.some((m) => m.id === newMsg.id)) return prev;
          return [...prev, newMsg];
        });
      } catch (err) {
        console.error("Failed to send message via REST fallback:", err);
      }
    }
  };

  const handleInputTyping = (isTyping: boolean) => {
    if (activeConversationId) {
      sendTyping(activeConversationId, isTyping);
    }
  };

  if (loading || (!user && !loading)) {
    return (
      <div className="h-screen w-screen bg-[#0c1317] flex items-center justify-center">
        <div className="w-10 h-10 border-4 border-[#00a884]/20 border-t-[#00a884] rounded-full animate-spin mb-4" />
      </div>
    );
  }

  return (
    <div className="h-screen w-screen bg-[#0c1317] flex items-center justify-center overflow-hidden lg:p-4">
      <div className="w-full h-full lg:max-w-7xl lg:h-[96vh] bg-[#111b21] lg:rounded-2xl lg:border lg:border-[#222e35] flex overflow-hidden shadow-2xl shadow-black/80">
        {/* Left Sidebar: Conversations, New Chat, New Group */}
        <ChatSidebar
          currentUser={user}
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onStartDirectChat={handleStartDirectChat}
          onCreateGroupChat={handleCreateGroupChat}
          onLogout={logout}
        />

        {/* Right Chat Panel */}
        <main className="flex-1 flex flex-col h-full bg-[#0b141a] overflow-hidden">
          <ChatHeader
            conversation={activeConversation}
            currentUser={user}
            typingUser={activeConversationId ? typingMap[activeConversationId] || null : null}
            isConnected={isConnected}
            isReconnecting={isReconnecting}
          />

          {loadingMessages ? (
            <div className="flex-1 flex items-center justify-center bg-[#0b141a]">
              <div className="w-8 h-8 border-3 border-[#00a884]/20 border-t-[#00a884] rounded-full animate-spin" />
            </div>
          ) : (
            <MessageList
              messages={messages}
              currentUser={user}
              conversation={activeConversation}
            />
          )}

          <MessageInput
            onSendMessage={handleSendMessage}
            onTyping={handleInputTyping}
            disabled={!activeConversation}
            disabledPlaceholder={
              !activeConversation ? "Select a conversation from the sidebar to chat..." : undefined
            }
          />
        </main>
      </div>
    </div>
  );
}
