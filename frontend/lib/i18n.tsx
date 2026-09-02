"use client";
import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { getUserProfile, isAuthenticated } from "./auth";

export const SUPPORTED_LOCALES = ["en", "mr"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

const LOCALE_STORAGE_KEY = "dms_locale";
const CACHE_KEY_PREFIX = "dms_i18n_cache_";

function readCachedTranslations(locale: Locale): Record<string, string> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(CACHE_KEY_PREFIX + locale);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function writeCachedTranslations(locale: Locale, data: Record<string, string>): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(CACHE_KEY_PREFIX + locale, JSON.stringify(data));
  } catch {
    // best-effort cache; storage full/unavailable is not fatal
  }
}

function readInitialLocale(): Locale {
  if (typeof window === "undefined") return "en";
  const profile = getUserProfile();
  if (profile?.locale && (SUPPORTED_LOCALES as readonly string[]).includes(profile.locale)) {
    return profile.locale as Locale;
  }
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY);
  if (stored && (SUPPORTED_LOCALES as readonly string[]).includes(stored)) {
    return stored as Locale;
  }
  return "en";
}

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, fallback: string) => string;
  isReady: boolean;
}

const I18nContext = createContext<I18nContextValue | null>(null);

/** T95 — only ~48 keys covering auth pages, the drive header, and common
 * action words are actually translated (see backend migration
 * 0032_i18n_translations). t() falls back to the English string passed
 * inline for every key not in that set, so untranslated UI degrades to
 * English rather than showing a blank string or a raw key. */
export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setLocaleState(readInitialLocale());

    // The synchronous read above only sees a profile already cached in
    // this browser. Fetch it explicitly so a locale saved from another
    // device (via PATCH /auth/me/locale) takes effect on first load here
    // too, not just after some other component happens to call getProfile.
    if (isAuthenticated()) {
      api.auth
        .getProfile()
        .then((data) => {
          if (data?.locale && (SUPPORTED_LOCALES as readonly string[]).includes(data.locale)) {
            setLocaleState(data.locale as Locale);
          }
        })
        .catch(() => {
          // offline/unreachable — the synchronous read above already stands
        });
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    const cached = readCachedTranslations(locale);
    if (cached) {
      setTranslations(cached);
      setIsReady(true);
    }

    api.i18n
      .getTranslations(locale)
      .then((data) => {
        if (cancelled || !data || typeof data !== "object") return;
        setTranslations(data);
        writeCachedTranslations(locale, data);
        setIsReady(true);
      })
      .catch(() => {
        // Network/offline: fall back to whatever was cached (possibly
        // none), t()'s inline fallback still keeps the UI readable.
        setIsReady(true);
      });

    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
      document.documentElement.classList.toggle("font-devanagari", locale === "mr");
    }

    return () => {
      cancelled = true;
    };
  }, [locale]);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    if (typeof window !== "undefined") {
      localStorage.setItem(LOCALE_STORAGE_KEY, next);
    }
    if (isAuthenticated()) {
      api.auth.updateLocale(next).catch(() => {
        // Best-effort persistence — the localStorage write above already
        // makes the switch take effect immediately in this browser.
      });
    }
  }, []);

  const t = useCallback(
    (key: string, fallback: string) => translations[key] ?? fallback,
    [translations]
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, isReady }),
    [locale, setLocale, t, isReady]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}
