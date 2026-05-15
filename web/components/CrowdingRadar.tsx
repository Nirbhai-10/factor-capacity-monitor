"use client";
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Radar, ResponsiveContainer,
} from "recharts";

export function CrowdingRadar({ data }: { data: Record<string, number> }) {
  const points = Object.entries(data).map(([k, v]) => ({
    signal: k.replace(/_/g, " "), score: Math.round(v),
  }));
  return (
    <ResponsiveContainer width="100%" height={300}>
      <RadarChart data={points} outerRadius={100}>
        <PolarGrid stroke="#e6e3da" />
        <PolarAngleAxis dataKey="signal"
                         tick={{ fontSize: 11, fill: "#5a5a5a",
                                  fontFamily: "'Source Serif 4', serif" }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar name="latest" dataKey="score" stroke="#1a3a5c"
                fill="#1a3a5c" fillOpacity={0.18} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
