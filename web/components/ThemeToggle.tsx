"use client";

import { useEffect, useState } from "react";

// Light/dark toggle. The actual theme is applied to <html data-theme> before paint by the inline
// script in layout.tsx (no flash); this just flips it and persists the choice.
export function ThemeToggle() {
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  useEffect(() => {
    setTheme(document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark");
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    if (next === "light") document.documentElement.setAttribute("data-theme", "light");
    else document.documentElement.removeAttribute("data-theme");
    try {
      localStorage.setItem("astova-theme", next);
    } catch {
      /* storage blocked — the toggle still works for the session */
    }
  };

  return (
    <button
      onClick={toggle}
      aria-label="Toggle light or dark theme"
      title={theme === "dark" ? "Switch to light" : "Switch to dark"}
      style={{
        width: 32,
        height: 32,
        borderRadius: 8,
        border: "1px solid var(--border)",
        background: "var(--surface)",
        color: "var(--text-2)",
        cursor: "pointer",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 14,
        flexShrink: 0,
        lineHeight: 1,
      }}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
