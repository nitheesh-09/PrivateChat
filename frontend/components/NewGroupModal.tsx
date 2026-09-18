"use client";

import React, { useState, useEffect } from "react";
import { User } from "@/lib/types";
import { api } from "@/lib/api";
import { getInitials } from "@/lib/utils";
import { X, Users, Check, AlertCircle } from "lucide-react";

interface NewGroupModalProps {
  isOpen: boolean;
  currentUser: User | null;
  onClose: () => void;
  onCreateGroup: (name: string, memberIds: string[]) => Promise<void>;
}

export function NewGroupModal({ isOpen, currentUser, onClose, onCreateGroup }: NewGroupModalProps) {
  const [name, setName] = useState("");
  const [users, setUsers] = useState<User[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setUsers([]);
      setName("");
      setSelectedIds(new Set());
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);
    setName("");
    setSelectedIds(new Set());
    api.getUsers()
      .then((data) => {
        const filtered = currentUser
          ? data.filter((u) => u.id !== currentUser.id && u.username.toLowerCase() !== currentUser.username.toLowerCase())
          : data;
        setUsers(filtered);
      })
      .catch((err) => console.error("Error loading users:", err))
      .finally(() => setLoading(false));
  }, [isOpen, currentUser?.id]);

  if (!isOpen) return null;

  const toggleUser = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Please enter a group name.");
      return;
    }

    setSubmitting(true);
    try {
      await onCreateGroup(trimmed, Array.from(selectedIds));
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Failed to create group.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      <div className="bg-[#111b21] border border-[#222e35] rounded-2xl w-full max-w-md overflow-hidden shadow-2xl flex flex-col max-h-[85vh] animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="h-14 bg-[#202c33] px-5 flex items-center justify-between border-b border-[#222e35]">
          <div className="flex items-center gap-2 text-[#e9edef] font-semibold text-sm">
            <Users className="w-4 h-4 text-[#00a884]" />
            <span>Create New Group</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-[#8696a0] hover:text-[#e9edef] rounded-lg hover:bg-[#111b21] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="m-3 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
          {/* Group Name input */}
          <div className="p-4 border-b border-[#222e35] bg-[#111b21]">
            <label className="block text-xs font-medium text-[#8696a0] mb-1.5 uppercase tracking-wider">
              Group Subject
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. College Friends, Weekend Trip..."
              maxLength={100}
              required
              className="w-full bg-[#202c33] border border-[#2a3942] focus:border-[#00a884] focus:ring-1 focus:ring-[#00a884] rounded-xl px-3.5 py-2 text-sm text-[#e9edef] placeholder-[#8696a0] outline-none"
              autoFocus
            />
          </div>

          {/* Members Selector Title */}
          <div className="px-4 py-2 bg-[#182229] border-b border-[#222e35] flex items-center justify-between text-xs text-[#8696a0]">
            <span>Select Participants</span>
            <span className="text-[#00a884] font-medium">{selectedIds.size} selected</span>
          </div>

          {/* Users List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {loading ? (
              <div className="py-12 flex justify-center">
                <div className="w-8 h-8 border-3 border-[#00a884]/20 border-t-[#00a884] rounded-full animate-spin" />
              </div>
            ) : users.length === 0 ? (
              <div className="py-8 text-center text-xs text-[#8696a0]">
                No other registered users available to add.
              </div>
            ) : (
              users.map((u) => {
                const isSelected = selectedIds.has(u.id);
                return (
                  <button
                    type="button"
                    key={u.id}
                    onClick={() => toggleUser(u.id)}
                    className={`w-full flex items-center gap-3 p-2 rounded-xl transition-colors text-left cursor-pointer ${
                      isSelected ? "bg-[#2a3942]/60" : "hover:bg-[#202c33]"
                    }`}
                  >
                    <div
                      className={`w-5 h-5 rounded-md border flex items-center justify-center shrink-0 transition-colors ${
                        isSelected
                          ? "bg-[#00a884] border-[#00a884] text-[#111b21]"
                          : "border-[#8696a0]/50 bg-transparent"
                      }`}
                    >
                      {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>

                    <div className="w-8 h-8 rounded-full bg-[#202c33] text-[#d1d7db] font-semibold flex items-center justify-center text-xs border border-[#2a3942]">
                      {getInitials(u.username)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-[#e9edef] truncate">
                        {u.username}
                      </div>
                      <div className="text-[11px] text-[#8696a0]">
                        {u.is_online ? <span className="text-[#00a884]">Online</span> : "Offline"}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Footer actions */}
          <div className="p-3 bg-[#202c33] border-t border-[#222e35] flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-[#8696a0] hover:text-[#e9edef] rounded-xl transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !name.trim()}
              className="px-5 py-2 bg-[#00a884] hover:bg-[#02be94] disabled:opacity-40 disabled:hover:bg-[#00a884] text-[#111b21] font-semibold text-xs rounded-xl transition-all cursor-pointer shadow-md"
            >
              {submitting ? "Creating..." : "Create Group"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
