"use client";
import { useCallback, useRef } from "react";

// Real bug found live 2026-09-02: drive rows/cards had both onClick (toggle
// select) and onDoubleClick (open preview / navigate into folder) on the
// same element. Two ordinary clicks used to select a file then immediately
// unselect it -- a completely normal "click it, click it again" gesture --
// land close enough together for the browser to *also* fire a native
// dblclick event alongside the two click events. That made the preview
// modal (or folder navigation) pop open at the same moment the row was
// deselected underneath it, so the deselect looked like it "didn't work"
// -- the user just couldn't see it happen because a modal/navigation
// covered it.
//
// Fix: debounce the single-click action by DBLCLICK_WINDOW_MS. If a second
// click for the same key arrives inside that window, the pending single
// click is cancelled outright (no select/deselect fires) and the browser's
// dblclick handler runs instead. Two clicks spaced further apart still
// toggle selection normally, just with a small (intentional) delay before
// the visual state updates.
const DBLCLICK_WINDOW_MS = 220;

export function useDebouncedActivation() {
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  const handleClick = useCallback((key: string, onSingleClick: () => void) => {
    if (timers.current[key]) {
      clearTimeout(timers.current[key]);
      delete timers.current[key];
      return;
    }
    timers.current[key] = setTimeout(() => {
      delete timers.current[key];
      onSingleClick();
    }, DBLCLICK_WINDOW_MS);
  }, []);

  const handleDoubleClick = useCallback((key: string, onDoubleClick: () => void) => {
    if (timers.current[key]) {
      clearTimeout(timers.current[key]);
      delete timers.current[key];
    }
    onDoubleClick();
  }, []);

  return { handleClick, handleDoubleClick };
}
