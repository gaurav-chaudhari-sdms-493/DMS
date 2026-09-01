"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { getBaseUrl } from "@/lib/api";

interface I18nContextType {
  locale: "en" | "mr";
  setLocale: (locale: "en" | "mr") => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocale] = useState<"en" | "mr">("en");
  const [translations, setTranslations] = useState<Record<string, string>>({
    "workbench.title": "Verification Workbench",
    "workbench.back": "Back to Drive",
    "entity.title": "Entity 360",
    "entity.records": "Records",
    "entity.linked_entities": "Linked entities",
    "entity.linked_facts": "Linked facts",
    "entity.load": "Load",
    "entity.view_history": "View history",
    "workbench.queue": "Queue",
    "workbench.selected_fact": "Selected fact",
    "workbench.bulk_confirm": "Bulk confirm (T54)",
    "workbench.bulk_edit": "Bulk edit (T80)",
    "nav.logout": "Logout",
    "entity.attributes": "Attributes",
    "entity.node_id_placeholder": "Entity node ID",
  });

  useEffect(() => {
    fetch(`${getBaseUrl()}/api/v1/i18n/${locale}`)
      .then((res) => {
        if (!res.ok) throw new Error("Network response was not ok");
        return res.json();
      })
      .then((data) => setTranslations(data))
      .catch((err) => console.error("Failed to load translations:", err));
  }, [locale]);

  const t = (key: string) => {
    return translations[key] || key;
  };

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return context;
}
