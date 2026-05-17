export function Kpi({ label, value, hint }: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="card flex flex-col gap-1">
      <div className="text-[0.78rem] uppercase tracking-[0.12em] text-muted">{label}</div>
      <div className="font-serif text-3xl text-ink leading-tight">{value}</div>
      {hint && <div className="text-xs text-muted mt-1">{hint}</div>}
    </div>
  );
}
