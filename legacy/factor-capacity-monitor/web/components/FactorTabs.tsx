"use client";
import { useState } from "react";
import clsx from "clsx";

export function FactorTabs({
  factors, current, onChange,
}: {
  factors: string[];
  current: string;
  onChange: (f: string) => void;
}) {
  return (
    <nav className="flex gap-6 border-b border-rule mb-8">
      {factors.map((f) => (
        <button key={f}
                onClick={() => onChange(f)}
                className={clsx(
                  "pb-2 -mb-px font-serif text-lg transition-colors",
                  f === current ? "text-accent border-b-2 border-accent" : "text-muted hover:text-ink"
                )}>
          {f}
        </button>
      ))}
    </nav>
  );
}
