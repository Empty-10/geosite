export function Logo({ size = 22 }: { size?: number }) {
  const inset = Math.round(size * 0.18);
  return (
    <div
      style={{
        width: size,
        height: size,
        border: "1.5px solid var(--accent)",
        transform: "rotate(45deg)",
        borderRadius: 3,
        position: "relative",
      }}
      aria-hidden
    >
      <div
        style={{
          position: "absolute",
          inset,
          background: "var(--accent)",
          borderRadius: 1,
        }}
      />
    </div>
  );
}
