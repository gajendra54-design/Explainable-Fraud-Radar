import { Monitoring } from "./pages/Monitoring";
import type { User } from "./types/api";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Radar,
  LayoutDashboard,
  ArrowLeftRight,
  FolderSearch,
  ChartNoAxesCombined,
  Activity,
  Database,
  LogOut,
  ChevronRight,
  Bell,
  ShieldCheck,
} from "lucide-react";
import { api, hasToken, setToken } from "./api/client";
import {
  Overview,
  Transactions,
  Investigation,
  Evaluation,
  Administration,
} from "./pages/Views";
const loginSchema = z.object({
  username: z.string().min(1, "Enter your username"),
  password: z.string().min(1, "Enter your password"),
});
const nav = [
  { id: "overview", name: "Overview", icon: LayoutDashboard },
  { id: "transactions", name: "Transactions", icon: ArrowLeftRight },
  { id: "cases", name: "Investigations", icon: FolderSearch },
  { id: "evaluation", name: "Model evaluation", icon: ChartNoAxesCombined },
  { id: "monitoring", name: "Monitoring", icon: Activity },
  { id: "pipeline", name: "Data & models", icon: Database },
];
export default function App() {
  const [loggedIn, setLoggedIn] = useState(hasToken());
  const [page, setPage] = useState("overview");
  const [transaction, setTransaction] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [logoutError, setLogoutError] = useState("");
  const client = useQueryClient();
  const form = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
  });
  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => api<User>("/auth/me"),
    enabled: loggedIn,
  });
  const go = (p: string) => {
    setPage(p);
    setTransaction(null);
  };
  const open = (id: string) => {
    setTransaction(id);
    setPage("transactions");
  };
  if (!loggedIn)
    return (
      <main className="login-shell">
        <section className="login-story">
          <div className="brand">
            <Radar size={36} />
            <span>
              fraud<span className="brand-light">radar</span>
              <small>EXPLAINABLE INTELLIGENCE</small>
            </span>
          </div>
          <span className="eyebrow">SEE THE SIGNAL. UNDERSTAND THE WHY.</span>
          <h1>
            Every risk score
            <br />
            has a story.
          </h1>
          <p>
            Bring transaction intelligence, transparent model explanations and
            thoughtful investigation into one workspace.
          </p>
          <div className="radar-art">
            <i />
            <i />
            <i />
            <b />
            <span />
          </div>
          <small>Synthetic data. Human decisions. Explainable by design.</small>
        </section>
        <section className="login-form">
          <div className="badge low">
            <ShieldCheck size={13} /> SYNTHETIC DEMONSTRATION
          </div>
          <h2>Welcome to your workspace</h2>
          <p>Sign in to review signals and investigate with context.</p>
          <form
            onSubmit={form.handleSubmit(async (values) => {
              setError("");
              try {
                const data = await api<{ access_token: string; user: User }>(
                  "/auth/login",
                  values,
                );
                setToken(data.access_token);
                setLoggedIn(true);
              } catch (e) {
                setError((e as Error).message);
              }
            })}
          >
            <label>
              Username
              <input autoComplete="username" {...form.register("username")} />
            </label>
            {form.formState.errors.username && (
              <small className="error">
                {form.formState.errors.username.message}
              </small>
            )}
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                {...form.register("password")}
              />
            </label>
            {form.formState.errors.password && (
              <small className="error">
                {form.formState.errors.password.message}
              </small>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary" disabled={form.formState.isSubmitting}>
              {" "}
              {form.formState.isSubmitting ? "Signing in…" : "Enter workspace"}
              <ChevronRight size={16} />
            </button>
          </form>
          <p className="login-note">
            Use the account configured during setup. This environment contains
            generated transactions only.
          </p>
        </section>
      </main>
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Radar size={32} />
          <span>
            fraud<span className="brand-light">radar</span>
            <small>EXPLAINABLE INTELLIGENCE</small>
          </span>
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav>
          {nav.map((n) => (
            <button
              key={n.id}
              aria-label={n.name}
              title={n.name}
              className={page === n.id ? "selected" : ""}
              onClick={() => go(n.id)}
            >
              <n.icon size={19} />
              <span>{n.name}</span>
              {page === n.id && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {logoutError && (
            <p className="session-error" role="alert">
              Sign out failed: {logoutError}
            </p>
          )}
          <div className="demo-label">
            <span />
            Synthetic environment
          </div>
          <p>
            Risk signals support review.
            <br />
            They do not establish fraud.
          </p>
          <button
            aria-label="Sign out"
            title="Sign out"
            className="profile"
            onClick={async () => {
              try {
                await api("/auth/logout", {});
              } catch (e) {
                setLogoutError((e as Error).message);
                return;
              }
              setToken("");
              client.clear();
              setLoggedIn(false);
            }}
          >
            <span className="avatar">
              {me.data?.username?.slice(0, 2).toUpperCase() || "FR"}
            </span>
            <span>
              {me.data?.username || "Workspace user"}
              <small>{me.data?.role || "Authenticated"}</small>
            </span>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            Workspace <ChevronRight size={13} />
            <strong>{nav.find((n) => n.id === page)?.name}</strong>
          </div>
          <div>
            <span className="environment">
              <span /> DEMO · SYNTHETIC DATA
            </span>
            <Bell size={18} />
          </div>
        </header>
        <main className="content">
          {page === "overview" && <Overview open={open} go={go} />}{" "}
          {page === "transactions" && (
            <Transactions
              selected={transaction}
              open={open}
              close={() => setTransaction(null)}
            />
          )}{" "}
          {page === "cases" && <Investigation open={open} />}{" "}
          {page === "evaluation" && <Evaluation />}{" "}
          {page === "monitoring" && <Monitoring role={me.data?.role} />}{" "}
          {page === "pipeline" && <Administration role={me.data?.role} />}
        </main>
        <footer>
          EXPLAINABLE FRAUD RADAR{" "}
          <span>Decision support · Synthetic benchmark · Human oversight</span>
        </footer>
      </div>
    </div>
  );
}
