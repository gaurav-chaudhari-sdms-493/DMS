"use client";
import React from "react";
import { AlertTriangle, Info, CheckCircle2, X } from "lucide-react";

export interface ConfirmModalProps {
  isOpen: boolean;
  title?: string;
  message: string;
  type?: "danger" | "warning" | "info" | "success";
  confirmText?: string;
  cancelText?: string;
  showCancel?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmModal({
  isOpen,
  title,
  message,
  type = "danger",
  confirmText = "Confirm",
  cancelText = "Cancel",
  showCancel = true,
  onConfirm,
  onClose,
}: ConfirmModalProps) {
  if (!isOpen) return null;

  const getIcon = () => {
    switch (type) {
      case "danger":
      case "warning":
        return <AlertTriangle className="w-6 h-6 text-red-500 flex-shrink-0" />;
      case "success":
        return <CheckCircle2 className="w-6 h-6 text-emerald-500 flex-shrink-0" />;
      default:
        return <Info className="w-6 h-6 text-blue-500 flex-shrink-0" />;
    }
  };

  const getButtonBg = () => {
    switch (type) {
      case "danger":
        return "bg-red-600 hover:bg-red-700 text-white shadow-red-600/20";
      case "success":
        return "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-600/20";
      case "warning":
        return "bg-amber-600 hover:bg-amber-700 text-white shadow-amber-600/20";
      default:
        return "bg-[#0d2e5c] hover:bg-[#0945a5] text-white shadow-blue-600/20";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fadeIn select-none">
      <div
        role="presentation"
        className="w-full max-w-md bg-white border border-[#e1e3e1] rounded-3xl shadow-2xl overflow-hidden animate-scaleUp text-[#1f1f1f]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-2">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#f8fafd] rounded-2xl border border-[#e1e3e1]">
              {getIcon()}
            </div>
            <h3 className="text-lg font-bold text-[#1f1f1f]">
              {title || (type === "danger" ? "Confirm Action" : "Notice")}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-[#747775] hover:text-[#1f1f1f] rounded-full hover:bg-[#f0f4f9] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message Body */}
        <div className="px-6 py-4">
          <p className="text-sm text-[#444746] leading-relaxed whitespace-pre-wrap">
            {message}
          </p>
        </div>

        {/* Action Buttons Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 bg-[#f8fafd] border-t border-[#e1e3e1]">
          {showCancel && (
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold text-[#444746] hover:text-[#1f1f1f] hover:bg-[#e1e5ea] rounded-xl transition-all"
            >
              {cancelText}
            </button>
          )}

          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-5 py-2 text-sm font-semibold rounded-xl shadow-sm transition-all ${getButtonBg()}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
