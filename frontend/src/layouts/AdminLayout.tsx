import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, Outlet, useLocation } from "react-router-dom";

import { AdminNavigation } from "../components/navigation/AdminNavigation";
import { SiteBrand } from "../components/navigation/SiteBrand";
import { SkipLink } from "../components/navigation/SkipLink";
import { ErrorState } from "../components/feedback/ErrorState";
import { Spinner } from "../components/feedback/Loading";
import { Button } from "../components/ui/Button";
import { buttonClassName } from "../components/ui/buttonStyles";
import { logoutAdmin } from "../features/admin/api";
import { useAdminSession } from "../features/admin/useAdminSession";

export function AdminLayout() {
  const session = useAdminSession();
  const queryClient = useQueryClient();
  const location = useLocation();
  const logout = useMutation({
    mutationFn: () => logoutAdmin(session.data!.csrf_token),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["admin-session"] });
      queryClient.removeQueries({ queryKey: ["admin-dashboard"] });
      queryClient.removeQueries({ queryKey: ["admin-issues"] });
    },
  });

  if (session.isPending) {
    return <main className="admin-auth-state"><Spinner label="Verifying administrator session…" /></main>;
  }
  if (session.isError) {
    if ("status" in session.error && session.error.status === 401) {
      return <Navigate replace state={{ from: location.pathname }} to="/admin/login" />;
    }
    return (
      <main className="admin-auth-state">
        <ErrorState
          description={session.error.message}
          onRetry={() => void session.refetch()}
          title="Administrator session could not be verified"
        />
      </main>
    );
  }
  if (logout.isSuccess) {
    return <Navigate replace to="/admin/login" />;
  }

  return (
    <div className="admin-shell">
      <SkipLink />
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <SiteBrand />
          <span className="badge badge-neutral">Admin</span>
        </div>
        <AdminNavigation />
        <div className="admin-session-summary">
          <span>Signed in as</span>
          <strong>{session.data.username}</strong>
        </div>
        <Button
          isLoading={logout.isPending}
          onClick={() => logout.mutate()}
          size="small"
          variant="secondary"
        >
          Sign out
        </Button>
        <Link className={buttonClassName("ghost", "small")} to="/">
          ← Public site
        </Link>
      </aside>
      <div className="admin-main">
        <header className="admin-mobile-header">
          <SiteBrand compact />
          <span>Administration</span>
          <Button onClick={() => logout.mutate()} size="small" variant="ghost">Sign out</Button>
        </header>
        <main id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
