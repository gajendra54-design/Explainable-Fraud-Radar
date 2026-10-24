import { ReactNode } from "react";
import { AlertCircle, RotateCw } from "lucide-react";
export function Panel({
  title,
  eyebrow,
  children,
  action,
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          {eyebrow && <span className="eyebrow">{eyebrow}</span>}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Badge({ value }: { value?: string }) {
  return (
    <span
      className={`badge ${(value || "").toLowerCase().replaceAll(" ", "_")}`}
    >
      {value?.replaceAll("_", " ") || "Not scored"}
    </span>
  );
}
export function State({
  loading,
  error,
  retry,
  empty,
}: {
  loading?: boolean;
  error?: Error | null;
  retry?: () => void;
  empty?: boolean;
}) {
  if (loading)
    return (
      <div className="state">
        <RotateCw className="spin" size={22} />
        Loading live application data…
      </div>
    );
  if (error)
    return (
      <div className="state error" role="alert">
        <AlertCircle size={24} />
        <strong>Unable to load this view</strong>
        <span>{error.message}</span>
        <button onClick={retry}>Try again</button>
      </div>
    );
  if (empty) return <div className="state">No records match this view.</div>;
  return null;
}
export function Metric({
  label,
  value,
  detail,
  accent,
}: {
  label: string;
  value: ReactNode;
  detail: string;
  accent?: boolean;
}) {
  return (
    <div className={`metric ${accent ? "accent" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
