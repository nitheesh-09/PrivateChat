"use client";

import React from "react";
import { Message } from "@/lib/types";
import { formatMessageTime } from "@/lib/utils";
import { Check, CheckCheck } from "lucide-react";

interface MessageBubbleProps {
  message: Message;
  isMe: boolean;
  showSenderName?: boolean;
}

export function MessageBubble({ message, isMe, showSenderName }: MessageBubbleProps) {
  return (
    <div className={`flex w-full my-1 ${isMe ? "justify-end" : "justify-start"}`}>
      <div
        className={`relative max-w-[85%] sm:max-w-[70%] md:max-w-[60%] px-3.5 py-2 shadow-sm ${
          isMe
            ? "bg-[#005c4b] text-[#e9edef] rounded-2xl rounded-tr-xs"
            : "bg-[#202c33] text-[#e9edef] rounded-2xl rounded-tl-xs"
        }`}
      >
        {/* Sender name for group chats */}
        {showSenderName && (
          <div className="text-[12px] font-semibold text-[#53bdeb] mb-0.5 select-none">
            {message.sender_username}
          </div>
        )}

        {/* Message Content */}
        <div className="text-[14.5px] leading-relaxed whitespace-pre-wrap break-words pr-2">
          {message.content}
        </div>

        {/* Timestamp & Status footer */}
        <div className="flex items-center justify-end gap-1 mt-1 select-none float-right ml-3">
          <span className="text-[10.5px] text-[#8696a0]/90">
            {formatMessageTime(message.created_at)}
          </span>

          {isMe && (
            <span
              className="inline-flex items-center ml-0.5"
              title={
                message.status === "read"
                  ? "Read"
                  : message.status === "delivered"
                  ? "Delivered"
                  : "Sent"
              }
            >
              {message.status === "read" ? (
                <CheckCheck className="w-3.5 h-3.5 text-[#53bdeb]" />
              ) : message.status === "delivered" ? (
                <CheckCheck className="w-3.5 h-3.5 text-[#8696a0]" />
              ) : (
                <Check className="w-3.5 h-3.5 text-[#8696a0]" />
              )}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
