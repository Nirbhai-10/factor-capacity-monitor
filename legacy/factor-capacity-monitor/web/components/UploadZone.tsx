"use client";
import { useRef, useState } from "react";
import { parseCsv, sampleCsv } from "@/lib/engine/parse";
import type { Strategy } from "@/lib/engine/types";

export function UploadZone({
  onLoaded,
}: {
  onLoaded: (s: Strategy, source: "upload" | "sample") => void;
}) {
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  function handleFile(file: File) {
    setError(null);
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      const r = parseCsv(text, file.name.replace(/\.csv$/i, ""));
      if (!r.ok) {
        setError(r.error.message);
        return;
      }
      onLoaded(r.strategy, "upload");
    };
    reader.readAsText(file);
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files[0];
          if (f) handleFile(f);
        }}
        onClick={() => input.current?.click()}
        className={
          "border border-dashed text-center cursor-pointer transition-colors px-6 py-12 " +
          (drag ? "border-[var(--ink)] bg-[#f4f1e9]" : "border-[var(--rule)]")
        }
      >
        <div className="font-serif text-2xl text-ink mb-2">Drop a CSV or click to choose</div>
        <p className="text-sm text-[var(--muted)] max-w-prose mx-auto">
          Two columns: <code>date</code> and one of <code>ret</code>, <code>pnl%</code>,
          <code>nav</code> or <code>equity</code>. Daily granularity. Minimum 30 rows;
          best results past 252 trading days. We never upload your file off your
          browser &mdash; everything runs locally.
        </p>
        <input
          ref={input}
          type="file"
          accept=".csv,text/csv,text/plain"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </div>

      {error && (
        <div className="border-l-2 border-[#862f2f] pl-3 py-1 text-sm text-[#862f2f]">
          {error}
        </div>
      )}

      <div className="flex items-center gap-4 text-sm text-[var(--muted)]">
        <span>or</span>
        <button
          className="btn"
          onClick={() => {
            const sample = sampleCsv();
            const r = parseCsv(sample, "Sample (1y synthetic)");
            if (r.ok) onLoaded(r.strategy, "sample");
          }}
        >
          load a 1-year sample
        </button>
      </div>
    </div>
  );
}
