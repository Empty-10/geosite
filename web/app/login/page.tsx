"use client";

import { useActionState, useState } from "react";
import Link from "next/link";

import { authenticate, type AuthState } from "./actions";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [state, formAction, pending] = useActionState<AuthState, FormData>(
    authenticate,
    {},
  );

  const isSignup = mode === "signup";

  return (
    <main
      style={{
        minHeight: "100dvh",
        display: "grid",
        placeItems: "center",
        padding: "2rem 1.25rem",
        background: "var(--ink)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 380 }}>
        <Link
          href="/"
          style={{
            display: "inline-block",
            marginBottom: "1.5rem",
            color: "var(--text-2)",
            textDecoration: "none",
            fontSize: 14,
          }}
        >
          ← Astova
        </Link>

        <div
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 14,
            padding: "1.75rem",
          }}
        >
          <h1 style={{ fontSize: 22, fontWeight: 600, margin: "0 0 0.35rem" }}>
            {isSignup ? "Create your account" : "Sign in"}
          </h1>
          <p style={{ color: "var(--text-2)", fontSize: 14, margin: "0 0 1.5rem" }}>
            {isSignup
              ? "Start monitoring how AI engines see your site."
              : "Welcome back."}
          </p>

          <form action={formAction} style={{ display: "grid", gap: "0.85rem" }}>
            <input type="hidden" name="mode" value={mode} />

            <label style={{ display: "grid", gap: 6 }}>
              <span style={labelStyle}>Email</span>
              <input
                name="email"
                type="email"
                autoComplete="email"
                required
                placeholder="you@company.com"
                style={inputStyle}
              />
            </label>

            <label style={{ display: "grid", gap: 6 }}>
              <span style={labelStyle}>Password</span>
              <input
                name="password"
                type="password"
                autoComplete={isSignup ? "new-password" : "current-password"}
                required
                minLength={8}
                placeholder={isSignup ? "At least 8 characters" : "••••••••"}
                style={inputStyle}
              />
            </label>

            {state.error && (
              <p style={{ color: "var(--fail)", fontSize: 13, margin: 0 }}>
                {state.error}
              </p>
            )}
            {state.message && (
              <p style={{ color: "var(--accent)", fontSize: 13, margin: 0 }}>
                {state.message}
              </p>
            )}

            <button type="submit" disabled={pending} style={buttonStyle(pending)}>
              {pending
                ? "Working…"
                : isSignup
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>
        </div>

        <p
          style={{
            textAlign: "center",
            color: "var(--text-2)",
            fontSize: 14,
            marginTop: "1.25rem",
          }}
        >
          {isSignup ? "Already have an account?" : "No account yet?"}{" "}
          <button
            type="button"
            onClick={() => setMode(isSignup ? "login" : "signup")}
            style={{
              background: "none",
              border: "none",
              color: "var(--accent)",
              cursor: "pointer",
              fontSize: 14,
              padding: 0,
            }}
          >
            {isSignup ? "Sign in" : "Create one"}
          </button>
        </p>
      </div>
    </main>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: 13,
  color: "var(--text-2)",
};

const inputStyle: React.CSSProperties = {
  background: "var(--raised)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: "0.6rem 0.7rem",
  color: "var(--text)",
  fontSize: 15,
  outline: "none",
};

function buttonStyle(pending: boolean): React.CSSProperties {
  return {
    marginTop: "0.35rem",
    background: "var(--accent)",
    color: "var(--on-accent)",
    border: "none",
    borderRadius: 8,
    padding: "0.7rem",
    fontSize: 15,
    fontWeight: 600,
    cursor: pending ? "default" : "pointer",
    opacity: pending ? 0.7 : 1,
  };
}
