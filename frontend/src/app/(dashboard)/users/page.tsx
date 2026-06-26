"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { Users, Plus, Pencil, Trash2, Check, X, Loader2, ShieldCheck, User as UserIcon } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";
import { useCurrentUser } from "@/hooks/useCurrentUser";
import type { User } from "@/types";

interface UserFormData {
  name: string;
  email: string;
  password: string;
  role: "admin" | "operator";
  is_active: boolean;
}

const EMPTY_FORM: UserFormData = {
  name: "",
  email: "",
  password: "",
  role: "operator",
  is_active: true,
};

export default function UsersPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: currentUser, isLoading: loadingMe } = useCurrentUser();

  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form, setForm] = useState<UserFormData>(EMPTY_FORM);
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  // Guard — só admin acessa
  if (!loadingMe && currentUser && currentUser.role !== "admin") {
    router.replace("/dashboard");
    return null;
  }

  const { data: users = [], isLoading } = useQuery<User[]>({
    queryKey: ["users"],
    queryFn: () => api.get("/api/auth/users").then((r) => r.data),
    enabled: currentUser?.role === "admin",
  });

  const createMutation = useMutation({
    mutationFn: (data: UserFormData) => api.post("/api/auth/users", data),
    onSuccess: () => {
      toast.success("Usuário criado com sucesso");
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setShowModal(false);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Erro ao criar usuário");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<UserFormData> }) =>
      api.put(`/api/auth/users/${id}`, data),
    onSuccess: () => {
      toast.success("Usuário atualizado com sucesso");
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setShowModal(false);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Erro ao atualizar usuário");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/api/auth/users/${id}`),
    onSuccess: () => {
      toast.success("Usuário excluído");
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setConfirmDeleteId(null);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail ?? "Erro ao excluir usuário");
    },
  });

  function openCreate() {
    setEditingUser(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  }

  function openEdit(user: User) {
    setEditingUser(user);
    setForm({
      name: user.name,
      email: user.email,
      password: "",
      role: user.role as "admin" | "operator",
      is_active: user.is_active,
    });
    setShowModal(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editingUser) {
      const payload: any = {
        name: form.name,
        email: form.email,
        role: form.role,
        is_active: form.is_active,
      };
      if (form.password) payload.password = form.password;
      updateMutation.mutate({ id: editingUser.id, data: payload });
    } else {
      createMutation.mutate(form);
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending;

  if (loadingMe || isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-6 h-6 animate-spin text-muted" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Controle de Usuários</h1>
          <p className="text-muted text-sm mt-1">{users.length} usuário(s) cadastrado(s)</p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 bg-primary text-black font-semibold px-4 py-2.5 rounded-md hover:bg-primary/90 transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          Novo Usuário
        </button>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left px-4 py-3 text-muted font-medium">Nome</th>
              <th className="text-left px-4 py-3 text-muted font-medium">E-mail</th>
              <th className="text-left px-4 py-3 text-muted font-medium">Perfil</th>
              <th className="text-left px-4 py-3 text-muted font-medium">Status</th>
              <th className="text-left px-4 py-3 text-muted font-medium">Cadastro</th>
              <th className="px-4 py-3 text-muted font-medium w-24">Ações</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-b border-border/40 hover:bg-white/5 transition-colors">
                <td className="px-4 py-3 text-white font-medium">{user.name}</td>
                <td className="px-4 py-3 text-slate-400">{user.email}</td>
                <td className="px-4 py-3">
                  <RoleBadge role={user.role} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge active={user.is_active} />
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">
                  {(user as any).created_at ? formatDate((user as any).created_at) : "—"}
                </td>
                <td className="px-4 py-3">
                  {confirmDeleteId === user.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => deleteMutation.mutate(user.id)}
                        disabled={deleteMutation.isPending}
                        className="p-1 text-red-400 hover:text-red-300 transition-colors"
                        title="Confirmar exclusão"
                      >
                        {deleteMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="p-1 text-muted hover:text-white transition-colors"
                        title="Cancelar"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => openEdit(user)}
                        className="p-1 text-muted hover:text-white transition-colors"
                        title="Editar"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      {currentUser?.id !== user.id && (
                        <button
                          onClick={() => setConfirmDeleteId(user.id)}
                          className="p-1 text-muted hover:text-red-400 transition-colors"
                          title="Excluir"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  )}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-muted">
                  Nenhum usuário encontrado
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal criar/editar */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="bg-surface border border-border rounded-lg p-6 w-full max-w-md mx-4 space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-white font-semibold text-lg">
                {editingUser ? "Editar Usuário" : "Novo Usuário"}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-muted hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm text-slate-300 font-medium">Nome</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-white placeholder:text-muted focus:outline-none focus:border-primary"
                  placeholder="Nome completo"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm text-slate-300 font-medium">E-mail</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-white placeholder:text-muted focus:outline-none focus:border-primary"
                  placeholder="email@exemplo.com"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm text-slate-300 font-medium">
                  Senha {editingUser && <span className="text-muted font-normal">(deixe em branco para manter)</span>}
                </label>
                <input
                  type="password"
                  required={!editingUser}
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-white placeholder:text-muted focus:outline-none focus:border-primary"
                  placeholder={editingUser ? "••••••••" : "Mínimo 6 caracteres"}
                  minLength={editingUser ? undefined : 6}
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm text-slate-300 font-medium">Tipo de usuário</label>
                <div className="grid grid-cols-2 gap-2">
                  {(["admin", "operator"] as const).map((role) => (
                    <button
                      key={role}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, role }))}
                      className={cn(
                        "flex items-center gap-2 px-3 py-2.5 rounded-md border text-sm transition-colors",
                        form.role === role
                          ? "border-primary bg-primary/10 text-white"
                          : "border-border text-slate-400 hover:border-primary/50"
                      )}
                    >
                      {role === "admin" ? <ShieldCheck className="w-4 h-4" /> : <UserIcon className="w-4 h-4" />}
                      {role === "admin" ? "Admin" : "Operador"}
                    </button>
                  ))}
                </div>
              </div>

              {editingUser && (
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => setForm((f) => ({ ...f, is_active: !f.is_active }))}
                    className={cn(
                      "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none",
                      form.is_active ? "bg-primary" : "bg-white/20"
                    )}
                  >
                    <span
                      className={cn(
                        "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                        form.is_active ? "translate-x-6" : "translate-x-1"
                      )}
                    />
                  </button>
                  <span className="text-sm text-slate-300">
                    {form.is_active ? "Usuário ativo" : "Usuário inativo"}
                  </span>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-2 rounded-md border border-border text-slate-300 hover:text-white transition-colors text-sm"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isPending}
                  className="flex-1 flex items-center justify-center gap-2 bg-primary text-black font-semibold px-4 py-2 rounded-md hover:bg-primary/90 transition-colors text-sm disabled:opacity-60"
                >
                  {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingUser ? "Salvar" : "Criar usuário"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function RoleBadge({ role }: { role: string }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
      role === "admin"
        ? "bg-yellow-500/20 text-yellow-400"
        : "bg-blue-500/20 text-blue-400"
    )}>
      {role === "admin" ? <ShieldCheck className="w-3 h-3" /> : <UserIcon className="w-3 h-3" />}
      {role === "admin" ? "Admin" : "Operador"}
    </span>
  );
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={cn(
      "inline-block px-2 py-0.5 rounded-full text-xs font-medium",
      active ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
    )}>
      {active ? "Ativo" : "Inativo"}
    </span>
  );
}
