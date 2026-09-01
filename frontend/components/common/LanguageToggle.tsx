"use client";
import React from "react";
import { useI18n } from "./I18nProvider";

export function LanguageToggle() {
  const { locale, setLocale } = useI18n();

  return (
    <button
      onClick={() => setLocale(locale === "en" ? "mr" : "en")}
      className="flex items-center justify-center w-8 h-8 rounded-full bg-[#f0f4f9] text-[#444746] hover:bg-[#e1e3e1] transition-colors text-xs font-bold"
      title="Toggle Language"
    >
      {locale === "en" ? "EN" : "MR"}
    </button>
  );
}
