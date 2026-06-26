import { useQuery } from "@tanstack/react-query";
import { getMe } from "@/lib/auth";
import type { User } from "@/types";

export function useCurrentUser() {
  return useQuery<User>({
    queryKey: ["me"],
    queryFn: getMe,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
