"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Home, Upload, Table2, FileDown, Sun, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";
import { logout } from "@/lib/auth";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/results", label: "Resultados", icon: Table2 },
  { href: "/reports", label: "Relatórios", icon: FileDown },
];

export function Sidebar() {
  const path = usePathname();

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface border-r border-border flex flex-col">
      <div className="flex items-center gap-3 px-6 py-5 border-b border-border">
        <Sun className="text-primary w-7 h-7" />
        <span className="text-white font-bold text-lg">PrevSolar</span>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
              path === href
                ? "bg-primary/15 text-primary"
                : "text-slate-400 hover:bg-white/5 hover:text-white"
            )}
          >
            <Icon className="w-4 h-4" />
            {label}
          </Link>
        ))}
      </nav>

      <button
        onClick={logout}
        className="flex items-center gap-3 px-6 py-4 text-sm text-slate-400 hover:text-white border-t border-border transition-colors"
      >
        <LogOut className="w-4 h-4" />
        Sair
      </button>
    </aside>
  );
}
