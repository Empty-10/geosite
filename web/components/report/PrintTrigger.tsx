"use client";

// Opens the browser print / "Save as PDF" dialog once the print report has rendered. No UI.
import { useEffect } from "react";

export function PrintTrigger() {
  useEffect(() => {
    const t = setTimeout(() => window.print(), 500); // let fonts/layout settle first
    return () => clearTimeout(t);
  }, []);
  return null;
}
