"use client";

import React from "react";
import { Wifi, Sparkles, AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface OnlineWarningModalProps {
  isOpen: boolean;
  onClose: () => void;
  featureName?: string;
  onRetry?: () => void;
}

export default function OnlineWarningModal({
  isOpen,
  onClose,
  featureName = "AI Search & Chat",
  onRetry,
}: OnlineWarningModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-md glass p-6 rounded-2xl border border-amber-500/30 bg-surface/90 shadow-2xl overflow-hidden">
        {/* Decorative Top Gradient */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-amber-500 via-primary to-secondary" />

        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg text-textMuted hover:text-textMain hover:bg-surface transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-amber-500/20 text-amber-400 flex items-center justify-center shadow-[0_0_20px_rgba(245,158,11,0.25)] shrink-0">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-textMain flex items-center gap-2">
              Internet Connection Required
            </h3>
            <p className="text-xs text-amber-400/90 font-medium">
              Offline Limitation Notice
            </p>
          </div>
        </div>

        <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 mb-6 text-sm text-textMuted leading-relaxed flex gap-3">
          <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-textMain mb-1">
              {featureName} is an online feature
            </p>
            <p className="text-xs text-textMuted">
              AI model inference, semantic vector search, and chat context processing require an active network connection to our AI servers. Please reconnect to the internet to access AI capabilities.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <Button variant="ghost" size="md" onClick={onClose}>
            Close
          </Button>
          {onRetry && (
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                onRetry();
                onClose();
              }}
              className="bg-amber-500 hover:bg-amber-600 border-none text-black font-semibold"
            >
              <Wifi className="w-4 h-4 mr-2" />
              Check Connection
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
