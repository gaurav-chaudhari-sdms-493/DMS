const EN_TO_MR_DIGITS: Record<string, string> = {
  "0": "०", "1": "१", "2": "२", "3": "३", "4": "४",
  "5": "५", "6": "६", "7": "७", "8": "८", "9": "९",
};

/** T95 — converts ASCII 0-9 digits within a string to Devanagari digits.
 * Non-digit characters (dates' "/", numbers' ",", currency symbols) pass
 * through unchanged, so a formatted string like "12/03/2026" becomes
 * "१२/०३/२०२६" rather than needing separate date-specific logic. */
export function toMarathiDigits(input: string | number): string {
  return String(input).replace(/[0-9]/g, (d) => EN_TO_MR_DIGITS[d]);
}

/** Formats a number/date-derived string in the given locale — passes
 * through unchanged for 'en', converts digits for 'mr'. */
export function localizeDigits(input: string | number, locale: string): string {
  return locale === "mr" ? toMarathiDigits(input) : String(input);
}
