"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";
import { Zap, Images, ScanLine, TrendingUp } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: string | number; icon: React.ElementType; color: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <p className="text-muted text-sm">{label}</p>
        <p className="text-white text-2xl font-bold">{value}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard"],
    queryFn: () => api.get("/api/results/dashboard").then((r) => r.data),
    refetchInterval: 15_000,
  });

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-muted">Carregando...</div>;
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-muted text-sm mt-1">Visão geral das análises fotovoltaicas</p>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Imagens enviadas" value={data?.total_images ?? 0} icon={Images} color="bg-blue-600" />
        <StatCard label="Processadas" value={data?.total_processed ?? 0} icon={ScanLine} color="bg-green-600" />
        <StatCard label="Painéis detectados" value={data?.total_panels ?? 0} icon={Zap} color="bg-yellow-500" />
        <StatCard label="Maior potencial (kWh/mês)" value={data?.highest_kwh_month?.toFixed(1) ?? "0"} icon={TrendingUp} color="bg-primary" />
      </div>

      <div className="bg-surface border border-border rounded-lg p-6">
        <h2 className="text-white font-semibold mb-4">Ranking — Potencial energético (kWh/mês)</h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data?.ranking ?? []} layout="vertical" margin={{ left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis type="number" stroke="#64748B" tick={{ fill: "#94A3B8", fontSize: 12 }} />
            <YAxis type="category" dataKey="original_name" stroke="#64748B" tick={{ fill: "#94A3B8", fontSize: 12 }} width={160} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1E293B", border: "1px solid #334155", borderRadius: 8 }}
              labelStyle={{ color: "#F8FAFC" }}
              formatter={(v: number) => [`${v.toFixed(1)} kWh/mês`, "Potencial"]}
            />
            <Bar dataKey="kwh_month" fill="#F59E0B" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
