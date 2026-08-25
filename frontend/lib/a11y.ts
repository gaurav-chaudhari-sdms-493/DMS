import type { KeyboardEvent } from "react";

/**
 * T96 — a keyboard equivalent for a click handler on a non-native
 * interactive element (a <div>/<tr> acting as a button or link).
 * Enter and Space both activate, matching native <button> behavior;
 * Space is prevented from scrolling the page the way it would on a
 * plain, non-interactive element.
 */
export function onKeyActivate<T = Element>(handler: (e: KeyboardEvent<T>) => void) {
  return (e: KeyboardEvent<T>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handler(e);
    }
  };
}
