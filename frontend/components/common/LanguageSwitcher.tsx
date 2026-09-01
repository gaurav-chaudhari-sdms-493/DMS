"use client";
import React from "react";
import { Languages } from "lucide-react";
import { useI18n, type Locale } from "@/lib/i18n";

const LOCALE_LABELS: Record<Locale, string> = {
  en: "English",
  mr: "मराठी",
};

interface LanguageSwitcherProps {
  className?: string;
}

/** T95 — language switcher: EN / मराठी. Used both pre-login (auth pages,
 * where the choice only persists to localStorage) and post-login (drive
 * header, where it also PATCHes the user's saved preference). */
export function LanguageSwitcher({ className = "" }: LanguageSwitcherProps) {
  const { locale, setLocale, t } = useI18n();

  return (
    <label className={`flex items-center gap-1.5 ${className}`}>
      <Languages className="w-4 h-4 text-[#444746]" aria-hidden="true" />
      <span className="sr-only">{t("header.language", "Language")}</span>
      <select
        aria-label={t("header.language", "Language")}
        value={locale}
        onChange={(e) => setLocale(e.target.value as Locale)}
        className="bg-transparent text-sm font-medium text-[#444746] hover:text-[#1f1f1f] focus:outline-none cursor-pointer"
      >
        {(Object.keys(LOCALE_LABELS) as Locale[]).map((code) => (
          <option key={code} value={code}>
            {LOCALE_LABELS[code]}
          </option>
        ))}
      </select>
    </label>
  );
}
