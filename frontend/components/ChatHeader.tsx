"use client";

import React from "react";
import { Conversation, User } from "@/lib/types";
import { formatLastSeen, getInitials } from "@/lib/utils";
import { Users, WifiOff, Shield } from "lucide-react";

interface ChatHeaderProps {
  conversation: Conversation | null;
  currentUser: User | null;
  typingUser: { username: string; isTyping: boolean } | null;
  isConnected: boolean;
  isReconnecting: boolean;
}

export function ChatHeader({
  conversation,
  currentUser,
  typingUser,
  isConnected,
  isReconnecting,
}: ChatHeaderProps) {
  if (!conversation) {
    return (
      <header className="h-16 bg-[#202c33] border-b border-[#222e35] px-4 flex items-center justify-between z-10 select-none">
        <span className="text-[#8696a0] text-sm italic">Select a conversation to start chatting</span>
      </header>
    );
  }

  const isGroup = conversation.type === "group";
  const partner = !isGroup
    ? conversation.members.find((m) => m.id !== currentUser?.id)
    : null;

  const memberNames = isGroup
    ? conversation.members.map((m) => m.username).join(", ")
    : "";

  return (
    <header className="h-16 bg-[#202c33] border-b border-[#222e35] px-4 flex items-center justify-between z-10 select-none">
      <div className="flex items-center space-x-3 min-w-0">
        {/* Avatar */}
        <div className="relative shrink-0">
          {isGroup ? (
            <div className="w-10 h-10 rounded-full bg-[#1e3a34] text-[#00a884] font-semibold flex items-center justify-center text-sm border border-[#00a884]/30 shadow-inner">
              <Users className="w-5 h-5" />
            </div>
          ) : (
            <div className="w-10 h-10 rounded-full bg-[#374248] text-[#d1d7db] font-semibold flex items-center justify-center text-sm border border-[#2a3942] shadow-sm">
              {getInitials(conversation.display_name)}
            </div>
          )}

          {!isGroup && partner?.is_online && (
            <span
              className="absolute bottom-0 right-0 w-3 h-3 bg-[#00a884] border-2 border-[#202c33] rounded-full animate-pulse"
              title="Online"
            />
          )}
        </div>

        {/* Title and subtitle info */}
        <div className="flex flex-col min-w-0">
          <span className="text-[#e9edef] font-medium text-base tracking-wide truncate">
            {conversation.display_name}
          </span>

          <div className="text-xs truncate transition-colors duration-200">
            {typingUser?.isTyping ? (
              <span className="text-[#00a884] font-medium flex items-center gap-1">
                {isGroup ? `${typingUser.username} is typing` : "typing"}
                <span className="animate-bounce">.</span>
                <span className="animate-bounce delay-100">.</span>
                <span className="animate-bounce delay-200">.</span>
              </span>
            ) : isGroup ? (
              <span className="text-[#8696a0] truncate" title={memberNames}>
                {conversation.members.length} members: {memberNames}
              </span>
            ) : partner ? (
              partner.is_online ? (
                <span className="text-[#00a884] font-medium">Online</span>
              ) : (
                <span className="text-[#8696a0]">{formatLastSeen(partner.last_seen)}</span>
              )
            ) : (
              <span className="text-[#8696a0]">Direct message</span>
            )}
          </div>
        </div>
      </div>

      {/* Right side connection info */}
      <div className="flex items-center space-x-3 shrink-0">
        {isReconnecting && (
          <div className="flex items-center gap-1.5 text-xs text-[#f59e0b] bg-[#f59e0b]/10 px-2.5 py-1 rounded-full border border-[#f59e0b]/20">
            <WifiOff className="w-3.5 h-3.5 animate-pulse" />
            <span>Reconnecting...</span>
          </div>
        )}

        <div
          className="flex items-center gap-1 text-[#8696a0] text-xs bg-[#111b21] px-2.5 py-1 rounded-full border border-[#222e35]"
          title={isGroup ? "Encrypted Group Session" : "Encrypted Direct Session"}
        >
          <Shield className="w-3.5 h-3.5 text-[#00a884]" />
          <span className="hidden sm:inline">{isGroup ? "Group Chat" : "Direct Chat"}</span>
        </div>
      </div>
    </header>
  );
}
