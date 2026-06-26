import { useQuery } from "@tanstack/react-query";

import { getAdminSession } from "./api";

export function useAdminSession() {
  return useQuery({
    queryKey: ["admin-session"],
    queryFn: ({ signal }) => getAdminSession(signal),
    retry: false,
    staleTime: 60_000,
  });
}
