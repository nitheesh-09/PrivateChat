"use client";

import React, { useState } from "react";
import { User, Conversation } from "@/lib/types";
import { formatMessageTime, getInitials } from "@/lib/utils";
import { LogOut, Plus, Users, MessageSquare, Search, Check, CheckCheck } from "lucide-react";
import { NewChatModal } from "./NewChatModal";
import { NewGroupModal } from "./NewGroupModal";

interface ChatSidebarProps {
  currentUser: User | null;
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onStartDirectChat: (userId: string) => Promise<void>;
  onCreateGroupChat: (name: string, memberIds: string[]) => Promise<void>;
  onLogout: () => void;
}

export function ChatSidebar({
  currentUser,
  conversations,
  activeConversationId,
  onSelectConversation,
  onStartDirectChat,
  onCreateGroupChat,
  onLogout,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("");
  const [isNewChatOpen, setIsNewChatOpen] = useState(false);
  const [isNewGroupOpen, setIsNewGroupOpen] = useState(false);

  const filteredConversations = conversations.filter((c) =>
    c.display_name.toLowerCase().includes(search.toLowerCase().trim()) ||
    (c.last_message?.content || "").toLowerCase().includes(search.toLowerCase().trim())
  );

  return (
    <aside className="w-full md:w-80 lg:w-96 bg-[#111b21] border-r border-[#222e35] flex flex-col h-full select-none">
      {/* Current User Top Bar */}
      <div className="h-16 bg-[#202c33] px-4 flex items-center justify-between border-b border-[#222e35]">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-[#00a884]/20 border border-[#00a884]/40 text-[#00a884] font-semibold flex items-center justify-center text-sm shadow-inner">
            {currentUser ? getInitials(currentUser.username) : "?"}
          </div>
          <div className="flex flex-col">
            <span className="text-[#e9edef] font-medium text-sm">
              {currentUser?.username || "You"}
            </span>
            <span className="text-[11px] text-[#8696a0] flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#00a884]" /> Active
            </span>
          </div>
        </div>

        <button
          onClick={onLogout}
          title="Log out"
          className="p-2 text-[#8696a0] hover:text-[#e9edef] hover:bg-[#111b21] rounded-full transition-colors cursor-pointer"
        >
          <LogOut className="w-5 h-5" />
        </button>
      </div>

      {/* Action Buttons: New Chat & New Group */}
      <div className="p-3 bg-[#111b21] border-b border-[#222e35] grid grid-cols-2 gap-2">
        <button
          onClick={() => setIsNewChatOpen(true)}
          className="flex items-center justify-center gap-1.5 py-2 px-3 bg-[#202c33] hover:bg-[#2a3942] active:scale-[0.98] text-[#e9edef] text-xs font-medium rounded-xl border border-[#2a3942] transition-all cursor-pointer shadow-xs"
        >
          <MessageSquare className="w-3.5 h-3.5 text-[#00a884]" />
          <span>New Chat</span>
        </button>

        <button
          onClick={() => setIsNewGroupOpen(true)}
          className="flex items-center justify-center gap-1.5 py-2 px-3 bg-[#202c33] hover:bg-[#2a3942] active:scale-[0.98] text-[#e9edef] text-xs font-medium rounded-xl border border-[#2a3942] transition-all cursor-pointer shadow-xs"
        >
          <Users className="w-3.5 h-3.5 text-[#00a884]" />
          <span>New Group</span>
        </button>
      </div>

      {/* Search Input */}
      <div className="px-3 py-2 border-b border-[#222e35]">
        <div className="flex items-center bg-[#202c33] rounded-xl px-3 py-1.5 border border-[#2a3942] focus-within:border-[#00a884]">
          <Search className="w-3.5 h-3.5 text-[#8696a0] mr-2 shrink-0" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search or start new chat"
            className="w-full bg-transparent text-xs text-[#e9edef] placeholder-[#8696a0] outline-none"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto">
        {filteredConversations.length === 0 ? (
          <div className="p-8 text-center text-[#8696a0]">
            <p className="text-xs">No conversations yet.</p>
            <p className="text-[11px] mt-1 text-[#8696a0]/70">
              Click &quot;New Chat&quot; or &quot;New Group&quot; above to start messaging!
            </p>
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            const lastMsg = conv.last_message;
            const isMe = lastMsg && currentUser && lastMsg.sender_id === currentUser.id;

            // Online indicator for direct chat
            const otherMember = conv.type === "direct" ? conv.members.find((m) => m.id !== currentUser?.id) : undefined;
            const isDirectPartnerOnline = Boolean(otherMember?.is_online);

            return (
              <div
                key={conv.id}
                onClick={() => onSelectConversation(conv.id)}
                className={`flex items-center gap-3 px-4 py-3 transition-colors cursor-pointer border-b border-[#222e35]/50 ${
                  isActive
                    ? "bg-[#2a3942] border-l-4 border-l-[#00a884]"
                    : "hover:bg-[#202c33]/70"
                }`}
              >
                {/* Avatar */}
                <div className="relative shrink-0">
                  {conv.type === "group" ? (
                    <div className="w-12 h-12 rounded-full bg-[#1e3a34] text-[#00a884] font-semibold flex items-center justify-center text-sm border border-[#00a884]/30 shadow-inner">
                      <Users className="w-5 h-5" />
                    </div>
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-[#374248] text-[#d1d7db] font-semibold flex items-center justify-center text-sm border border-[#2a3942]">
                      {getInitials(conv.display_name)}
                    </div>
                  )}

                  {conv.type === "direct" && isDirectPartnerOnline && (
                    <span className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-[#00a884] border-2 border-[#111b21] rounded-full" />
                  )}
                </div>

                {/* Conversation Details */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[#e9edef] font-medium text-sm truncate">
                      {conv.display_name}
                    </span>
                    {lastMsg && (
                      <span className="text-[11px] text-[#8696a0] shrink-0">
                        {formatMessageTime(lastMsg.created_at)}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1 text-xs text-[#8696a0] truncate pr-2">
                      {isMe && (
                        <span className="shrink-0">
                          {lastMsg?.status === "read" ? (
                            <CheckCheck className="w-3.5 h-3.5 text-[#53bdeb]" />
                          ) : lastMsg?.status === "delivered" ? (
                            <CheckCheck className="w-3.5 h-3.5 text-[#8696a0]" />
                          ) : (
                            <Check className="w-3.5 h-3.5 text-[#8696a0]" />
                          )}
                        </span>
                      )}

                      <span className="truncate">
                        {lastMsg ? (
                          conv.type === "group" && !isMe ? (
                            <><span className="text-[#d1d7db] font-medium">{lastMsg.sender_username}:</span> {lastMsg.content}</>
                          ) : (
                            lastMsg.content
                          )
                        ) : (
                          <span className="italic text-[#8696a0]/70">No messages yet</span>
                        )}
                      </span>
                    </div>

                    {conv.unread_count > 0 && (
                      <span className="shrink-0 bg-[#00a884] text-[#111b21] font-bold text-[11px] px-1.5 py-0.5 rounded-full min-w-[18px] text-center shadow-sm">
                        {conv.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modals */}
      <NewChatModal
        isOpen={isNewChatOpen}
        currentUser={currentUser}
        onClose={() => setIsNewChatOpen(false)}
        onSelectUser={onStartDirectChat}
      />
      <NewGroupModal
        isOpen={isNewGroupOpen}
        currentUser={currentUser}
        onClose={() => setIsNewGroupOpen(false)}
        onCreateGroup={onCreateGroupChat}
      />
    </aside>
  );
}
