"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Home, Upload, Table2, FileDown, Sun, LogOut, Users } from "lucide-react";
import { cn } from "@/lib/utils";
import { logout } from "@/lib/auth";
import { useCurrentUser } from "@/hooks/useCurrentUser";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: Home },
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/results", label: "Resultados", icon: Table2 },
  { href: "/reports", label: "Relatórios", icon: FileDown },
];

export function Sidebar() {
  const path = usePathname();
  const { data: currentUser } = useCurrentUser();
  const isAdmin = currentUser?.role === "admin";

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

        {isAdmin && (
          <>
            <div className="pt-3 pb-1 px-3">
              <p className="text-xs text-muted uppercase tracking-wider font-medium">Administração</p>
            </div>
            <Link
              href="/users"
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                path === "/users"
                  ? "bg-primary/15 text-primary"
                  : "text-slate-400 hover:bg-white/5 hover:text-white"
              )}
            >
              <Users className="w-4 h-4" />
              Controle de Usuários
            </Link>
          </>
        )}
      </nav>

      <div className="px-6 py-3 border-t border-border">
        {currentUser && (
          <div className="mb-3">
            <p className="text-white text-sm font-medium truncate">{currentUser.name}</p>
            <p className="text-muted text-xs truncate">{currentUser.email}</p>
            <span className={cn(
              "inline-block mt-1 text-xs px-2 py-0.5 rounded-full font-medium",
              isAdmin ? "bg-yellow-500/20 text-yellow-400" : "bg-blue-500/20 text-blue-400"
            )}>
              {isAdmin ? "Admin" : "Operador"}
            </span>
          </div>
        )}
        <button
          onClick={logout}
          className="flex items-center gap-3 text-sm text-slate-400 hover:text-white transition-colors w-full"
        >
          <LogOut className="w-4 h-4" />
          Sair
        </button>
      </div>
    </aside>
  );
}
