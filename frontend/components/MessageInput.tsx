"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";

interface MessageInputProps {
  onSendMessage: (content: string) => void;
  onTyping: (isTyping: boolean) => void;
  disabled: boolean;
  disabledPlaceholder?: string;
}

export function MessageInput({
  onSendMessage,
  onTyping,
  disabled,
  disabledPlaceholder,
}: MessageInputProps) {
  const [content, setContent] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isTypingRef = useRef(false);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [content]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
      return;
    }

    // Typing indicator management
    if (!isTypingRef.current) {
      isTypingRef.current = true;
      onTyping(true);
    }
    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    typingTimeoutRef.current = setTimeout(() => {
      isTypingRef.current = false;
      onTyping(false);
    }, 1500);
  };

  const handleSend = () => {
    const trimmed = content.trim();
    if (!trimmed || disabled) return;

    onSendMessage(trimmed);
    setContent("");

    if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
    isTypingRef.current = false;
    onTyping(false);

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.focus();
    }
  };

  return (
    <footer className="bg-[#202c33] px-4 py-3 flex items-end gap-3 border-t border-[#222e35] select-none">
      <div className="flex-1 bg-[#2a3942] rounded-xl flex items-center px-3 py-1.5 focus-within:ring-1 focus-within:ring-[#00a884]/60 transition-all">
        <textarea
          ref={textareaRef}
          rows={1}
          disabled={disabled}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled
              ? disabledPlaceholder || "Select a conversation to send a message..."
              : "Type a message... (Enter to send, Shift + Enter for new line)"
          }
          className="w-full bg-transparent text-[#e9edef] placeholder-[#8696a0] text-sm resize-none outline-none leading-relaxed max-h-[120px] overflow-y-auto disabled:cursor-not-allowed"
        />
      </div>

      <button
        onClick={handleSend}
        disabled={disabled || !content.trim()}
        title="Send message"
        className="w-10 h-10 rounded-full bg-[#00a884] text-[#111b21] flex items-center justify-center hover:bg-[#02be94] active:scale-95 disabled:opacity-40 disabled:hover:bg-[#00a884] disabled:active:scale-100 transition-all shrink-0 cursor-pointer disabled:cursor-not-allowed shadow-md"
      >
        <Send className="w-5 h-5 fill-current" />
      </button>
    </footer>
  );
}
