"use client";
import React from "react";
import { useI18n, type Locale } from "@/lib/i18n";

interface LanguageSwitcherProps {
  className?: string;
}

export function LanguageSwitcher({ className = "" }: LanguageSwitcherProps) {
  const { locale, setLocale, t } = useI18n();

  const toggleLocale = () => {
    setLocale(locale === "en" ? "mr" : "en");
  };

  return (
    <button
      onClick={toggleLocale}
      className={`flex items-center justify-center w-8 h-8 rounded-full bg-[#f0f4f9] text-[#444746] hover:bg-[#e1e3e1] transition-colors text-xs font-bold ${className}`}
      title={t("header.language", "Language")}
    >
      {locale === "en" ? "EN" : "MR"}
    </button>
  );
}
