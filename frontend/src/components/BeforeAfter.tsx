import { useRef, useState, useCallback } from "react";

export function BeforeAfter({
  before,
  after,
}: {
  before: string;
  after: string;
}) {
  const [pos, setPos] = useState(50);
  const ref = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const move = useCallback((clientX: number) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const pct = ((clientX - rect.left) / rect.width) * 100;
    setPos(Math.max(0, Math.min(100, pct)));
  }, []);

  return (
    <div
      ref={ref}
      className="relative w-full overflow-hidden rounded-2xl bg-black select-none glow"
      onMouseMove={(e) => dragging.current && move(e.clientX)}
      onMouseDown={(e) => {
        dragging.current = true;
        move(e.clientX);
      }}
      onMouseUp={() => (dragging.current = false)}
      onMouseLeave={() => (dragging.current = false)}
      onTouchMove={(e) => move(e.touches[0].clientX)}
    >
      <img src={before} alt="before" className="block w-full" draggable={false} />
      <div
        className="absolute inset-0 overflow-hidden"
        style={{ width: `${pos}%` }}
      >
        <img
          src={after}
          alt="after"
          className="block h-full max-w-none object-cover"
          style={{ width: ref.current?.clientWidth ?? "100%" }}
          draggable={false}
        />
      </div>

      {/* handle */}
      <div
        className="absolute inset-y-0 w-0.5 bg-white/90 shadow-[0_0_20px_rgba(255,255,255,0.6)]"
        style={{ left: `${pos}%` }}
      >
        <div className="absolute top-1/2 left-1/2 flex h-9 w-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full bg-white text-black text-xs font-bold shadow-lg">
          ⇆
        </div>
      </div>

      <span className="absolute bottom-3 left-3 rounded-full bg-black/60 px-3 py-1 text-[11px] font-bold tracking-wide text-rose-300 backdrop-blur">
        BEFORE
      </span>
      <span className="absolute bottom-3 right-3 rounded-full bg-black/60 px-3 py-1 text-[11px] font-bold tracking-wide text-emerald-300 backdrop-blur">
        AFTER
      </span>
    </div>
  );
}
