export function ZonePill({ zone }: { zone: string }) {
  return <span className={`zone-pill zone-${zone}`}>{zone}</span>;
}
