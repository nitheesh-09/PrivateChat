"use client";

import React, { useState, useEffect } from "react";
import { User } from "@/lib/types";
import { api } from "@/lib/api";
import { getInitials } from "@/lib/utils";
import { X, Search, User as UserIcon, MessageSquare } from "lucide-react";

interface NewChatModalProps {
  isOpen: boolean;
  currentUser: User | null;
  onClose: () => void;
  onSelectUser: (userId: string) => Promise<void>;
}

export function NewChatModal({ isOpen, currentUser, onClose, onSelectUser }: NewChatModalProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);

  // Helper to strictly exclude current user on frontend
  const filterOutCurrentUser = (rawUsers: User[]): User[] => {
    if (!currentUser) return rawUsers;
    return rawUsers.filter(
      (u) =>
        u.id !== currentUser.id &&
        u.username.toLowerCase().trim() !== currentUser.username.toLowerCase().trim()
    );
  };

  // Reset state when modal opens or closes or when user changes
  useEffect(() => {
    if (!isOpen) {
      setUsers([]);
      setSearch("");
      setLoading(false);
      setStarting(false);
      return;
    }

    let isMounted = true;
    setLoading(true);

    api.getUsers()
      .then((data) => {
        if (isMounted) {
          setUsers(filterOutCurrentUser(data));
        }
      })
      .catch((err) => console.error("Error loading users:", err))
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, currentUser?.id]);

  // Live backend search when typing
  useEffect(() => {
    if (!isOpen) return;

    const trimmedQuery = search.trim();
    if (!trimmedQuery) {
      // Reload full user list
      api.getUsers()
        .then((data) => setUsers(filterOutCurrentUser(data)))
        .catch((err) => console.error("Error reloading users:", err));
      return;
    }

    const timer = setTimeout(() => {
      setLoading(true);
      api.searchUsers(trimmedQuery)
        .then((data) => setUsers(filterOutCurrentUser(data)))
        .catch((err) => console.error("Search users error:", err))
        .finally(() => setLoading(false));
    }, 200);

    return () => clearTimeout(timer);
  }, [search, isOpen, currentUser?.id]);

  if (!isOpen) return null;

  const filteredUsers = filterOutCurrentUser(users);

  const handleSelect = async (userId: string) => {
    setStarting(true);
    try {
      await onSelectUser(userId);
      onClose();
    } catch (err) {
      console.error("Failed to start chat:", err);
    } finally {
      setStarting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-[#111b21] border border-[#222e35] rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="h-14 bg-[#202c33] px-5 flex items-center justify-between border-b border-[#222e35]">
          <div className="flex items-center gap-2 text-[#e9edef] font-semibold text-sm">
            <MessageSquare className="w-4 h-4 text-[#00a884]" />
            <span>Search users</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-[#8696a0] hover:text-[#e9edef] rounded-lg hover:bg-[#111b21] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Input */}
        <div className="p-3 border-b border-[#222e35] bg-[#111b21]">
          <div className="relative flex items-center bg-[#202c33] rounded-xl px-3 py-2 border border-[#2a3942] focus-within:border-[#00a884]">
            <Search className="w-4 h-4 text-[#8696a0] mr-2 shrink-0" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search users..."
              className="w-full bg-transparent text-sm text-[#e9edef] placeholder-[#8696a0] outline-none"
              autoFocus
            />
          </div>
        </div>

        {/* Users list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {loading ? (
            <div className="py-12 flex justify-center">
              <div className="w-8 h-8 border-3 border-[#00a884]/20 border-t-[#00a884] rounded-full animate-spin" />
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="py-12 text-center text-xs text-[#8696a0]">
              {search ? "No users matching your search." : "No other users registered yet."}
            </div>
          ) : (
            filteredUsers.map((u) => {
              const displayName = u.username.charAt(0).toUpperCase() + u.username.slice(1);
              return (
                <div
                  key={u.id}
                  className="w-full flex items-center justify-between p-2.5 rounded-xl hover:bg-[#202c33] transition-colors group"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="relative shrink-0">
                      <div className="w-10 h-10 rounded-full bg-[#202c33] group-hover:bg-[#2a3942] text-[#d1d7db] font-semibold flex items-center justify-center text-sm border border-[#2a3942]">
                        {getInitials(u.username)}
                      </div>
                      {u.is_online && (
                        <span className="absolute bottom-0 right-0 w-3 h-3 bg-[#00a884] border-2 border-[#111b21] rounded-full" />
                      )}
                    </div>

                    <div className="min-w-0">
                      <div className="text-sm font-medium text-[#e9edef] truncate">
                        {displayName}
                      </div>
                      <div className="text-xs text-[#8696a0] flex items-center gap-1.5">
                        <span className="text-[#00a884] font-medium">@{u.username}</span>
                        <span>•</span>
                        <span>{u.is_online ? "Online" : "Offline"}</span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleSelect(u.id)}
                    disabled={starting}
                    className="ml-3 px-3.5 py-1.5 bg-[#00a884]/20 hover:bg-[#00a884] text-[#00a884] hover:text-[#111b21] rounded-lg text-xs font-semibold transition-all shrink-0 cursor-pointer disabled:opacity-50"
                  >
                    {starting ? "Opening..." : "Message"}
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
