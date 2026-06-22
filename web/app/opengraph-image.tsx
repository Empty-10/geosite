import { ImageResponse } from "next/og";

export const alt = "damask — know exactly how AI engines see your site";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#0D0F12",
          color: "#E8EAED",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            width: 92,
            height: 92,
            border: "5px solid #19B36B",
            borderRadius: 16,
            transform: "rotate(45deg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 44,
          }}
        >
          <div style={{ width: 34, height: 34, background: "#19B36B", borderRadius: 5 }} />
        </div>
        <div style={{ fontSize: 88, fontWeight: 600, letterSpacing: "-3px" }}>damask</div>
        <div
          style={{
            fontSize: 34,
            color: "#9BA1A8",
            marginTop: 18,
            maxWidth: 800,
            textAlign: "center",
            lineHeight: 1.3,
          }}
        >
          Know exactly how AI engines see your site.
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginTop: 40,
            fontSize: 24,
            color: "#6B7178",
          }}
        >
          <div style={{ width: 12, height: 12, borderRadius: 12, background: "#19B36B" }} />
          verified fact, not hype
        </div>
      </div>
    ),
    { ...size },
  );
}
