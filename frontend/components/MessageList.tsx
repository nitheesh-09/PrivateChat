"use client";

import React, { useEffect, useRef } from "react";
import { Message, User, Conversation } from "@/lib/types";
import { formatDateDivider } from "@/lib/utils";
import { MessageBubble } from "./MessageBubble";
import { Shield, Sparkles } from "lucide-react";

interface MessageListProps {
  messages: Message[];
  currentUser: User | null;
  conversation: Conversation | null;
}

export function MessageList({ messages, currentUser, conversation }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!conversation) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center p-6 bg-[#0b141a] select-none">
        <div className="w-16 h-16 rounded-full bg-[#182229] border border-[#222e35] flex items-center justify-center mb-3 text-[#00a884]">
          <Shield className="w-8 h-8" />
        </div>
        <h3 className="text-[#e9edef] font-medium text-base mb-1">Private Chat</h3>
        <p className="text-xs text-[#8696a0] max-w-sm">
          Select a chat from the sidebar or click &quot;New Chat&quot; / &quot;New Group&quot; to begin messaging.
        </p>
      </div>
    );
  }

  const isGroup = conversation.type === "group";

  return (
    <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-4 bg-[#0b141a] relative flex flex-col">
      {/* Background ambient subtle pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(#ffffff 1px, transparent 1px)`,
          backgroundSize: "20px 20px",
        }}
      />

      {/* Security intro pill */}
      <div className="flex justify-center mb-6 mt-2">
        <div className="bg-[#182229] border border-[#222e35] text-[#8696a0] text-xs px-3.5 py-1.5 rounded-lg max-w-md text-center flex items-center gap-2 shadow-sm">
          <Shield className="w-4 h-4 text-[#00a884] shrink-0" />
          <span>
            {isGroup
              ? `Messages in this group are visible to all ${conversation.members.length} members.`
              : `Messages in this chat are private between you and ${conversation.display_name}.`}
          </span>
        </div>
      </div>

      {/* Messages */}
      {messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center p-6 select-none">
          <div className="w-16 h-16 rounded-full bg-[#182229] border border-[#222e35] flex items-center justify-center mb-3 text-[#00a884]">
            <Sparkles className="w-8 h-8" />
          </div>
          <h3 className="text-[#e9edef] font-medium text-base mb-1">No messages yet</h3>
          <p className="text-xs text-[#8696a0] max-w-xs">
            Send a message to kick off the conversation!
          </p>
        </div>
      ) : (
        <div className="flex flex-col space-y-1 z-0">
          {messages.map((message, index) => {
            const isMe = currentUser ? message.sender_id === currentUser.id : false;
            const prevMessage = index > 0 ? messages[index - 1] : null;

            const currentDate = formatDateDivider(message.created_at);
            const prevDate = prevMessage ? formatDateDivider(prevMessage.created_at) : null;
            const showDateDivider = currentDate !== prevDate;

            return (
              <React.Fragment key={message.id || index}>
                {showDateDivider && (
                  <div className="flex justify-center my-3">
                    <span className="bg-[#182229] border border-[#222e35] text-[#8696a0] text-[11.5px] font-medium px-3 py-1 rounded-md shadow-sm">
                      {currentDate}
                    </span>
                  </div>
                )}
                <MessageBubble
                  message={message}
                  isMe={isMe}
                  showSenderName={!isMe && isGroup}
                />
              </React.Fragment>
            );
          })}
        </div>
      )}

      {/* Scroll anchor */}
      <div ref={bottomRef} className="h-1" />
    </div>
  );
}
