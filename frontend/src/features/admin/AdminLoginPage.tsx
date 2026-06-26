import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { ApiError } from "../../api/client";
import { ErrorState } from "../../components/feedback/ErrorState";
import { Seo } from "../../components/Seo";
import { Button } from "../../components/ui/Button";
import { Card } from "../../components/ui/Card";
import { TextField } from "../../components/ui/FormField";
import { useAdminSession } from "./useAdminSession";
import { loginAdmin } from "./api";

export function AdminLoginPage() {
  const session = useAdminSession();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => loginAdmin(username, password),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin-session"], data);
      const destination =
        (location.state as { from?: string } | null)?.from ?? "/admin";
      void navigate(destination, { replace: true });
    },
  });

  if (session.isSuccess) {
    return <Navigate replace to="/admin" />;
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    login.mutate();
  }

  const errorMessage =
    login.error instanceof ApiError
      ? login.error.message
      : login.error instanceof Error
        ? login.error.message
        : undefined;

  return (
    <main className="admin-login-page" id="main-content">
      <Seo
        description="Restricted CivicPulse AI administrator sign-in."
        title="Administrator sign in"
      />
      <Card className="admin-login-card" padding="large">
        <div>
          <p className="eyebrow">Restricted administration</p>
          <h1>Administrator sign in</h1>
          <p className="page-copy">
            Manage civic issue status, public updates, and private reporter contact details.
          </p>
        </div>
        <form className="form-stack" onSubmit={submit}>
          <TextField
            autoComplete="username"
            label="Username"
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
          <TextField
            autoComplete="current-password"
            label="Password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          {errorMessage && (
            <ErrorState description={errorMessage} title="Sign in failed" />
          )}
          <Button isLoading={login.isPending} type="submit">
            Sign in securely
          </Button>
        </form>
      </Card>
    </main>
  );
}
