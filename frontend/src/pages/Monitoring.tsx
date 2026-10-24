import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, number, percent, date } from "../api/client";
import type { Drift, LivePerformance, DriftIncident, Page } from "../types/api";
import { Panel, Badge, State, Metric } from "../components/UI";
export function Monitoring({ role }: { role?: string }) {
  const client = useQueryClient();
  const [maturity, setMaturity] = useState(7);
  const [windowDays, setWindowDays] = useState(365);
  const drift = useQuery({
    queryKey: ["drift"],
    queryFn: () => api<Drift>("/monitoring/drift"),
  });
  const live = useQuery({
    queryKey: ["live-performance", maturity, windowDays],
    queryFn: () =>
      api<LivePerformance>(
        `/monitoring/live-performance?maturity_days=${maturity}&window_days=${windowDays}`,
      ),
  });
  const incidents = useQuery({
    queryKey: ["incidents"],
    queryFn: () => api<Page<DriftIncident>>("/monitoring/incidents"),
  });
  const [selected, setSelected] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [severity, setSeverity] = useState("warning");
  const create = useMutation({
    mutationFn: () =>
      api<DriftIncident>("/monitoring/incidents", { title, summary, severity }),
    onSuccess: (r) => {
      client.invalidateQueries({ queryKey: ["incidents"] });
      setSelected(r.id);
      setTitle("");
      setSummary("");
    },
  });
  const canInvestigate = role === "administrator" || role === "investigator";
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow">MODEL OBSERVABILITY</span>
          <h1>Keep the signals in perspective.</h1>
          <p>
            Monitor distributions, mature outcomes and accountable drift
            investigations.
          </p>
        </div>
      </div>
      <Panel
        title="Live verified-outcome performance"
        eyebrow="SEPARATE FROM THE SYNTHETIC BENCHMARK"
      >
        <div className="filters">
          <label>
            Maturity delay (days)
            <input
              aria-label="Maturity delay days"
              type="number"
              min="0"
              max="365"
              value={maturity}
              onChange={(e) =>
                setMaturity(Math.max(0, Math.min(365, Number(e.target.value))))
              }
            />
          </label>
          <label>
            Evaluation window (days)
            <input
              aria-label="Evaluation window days"
              type="number"
              min="1"
              max="3650"
              value={windowDays}
              onChange={(e) =>
                setWindowDays(
                  Math.max(1, Math.min(3650, Number(e.target.value))),
                )
              }
            />
          </label>
        </div>
        <State
          loading={live.isLoading}
          error={live.error}
          retry={() => live.refetch()}
        />
        {live.data && (
          <>
            <div className="metrics">
              <Metric
                label="Mature transactions"
                value={number(live.data.mature_count)}
                detail={`${number(live.data.immature_count)} still inside maturity delay`}
              />
              <Metric
                label="Verified labels"
                value={number(live.data.labeled_count)}
                detail="Independent verified outcomes"
              />
              <Metric
                label="Mature label coverage"
                value={percent(live.data.mature_label_coverage)}
                detail={`${number(live.data.mature_labeled_count)} mature labelled records`}
              />
              <Metric
                label="Window status"
                value={<Badge value={live.data.status} />}
                detail="Insufficient labels do not mean zero fraud"
              />
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Model version</th>
                    <th>Label coverage</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1</th>
                    <th>Degradation</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {live.data.models.map((m) => (
                    <tr key={m.model_version}>
                      <td className="mono">{m.model_version}</td>
                      <td>{percent(m.label_coverage)}</td>
                      <td>{percent(m.metrics?.precision)}</td>
                      <td>{percent(m.metrics?.recall)}</td>
                      <td>{number(m.metrics?.f1)}</td>
                      <td>
                        {!m.metrics || m.status !== "ready" || m.baseline_f1 == null || m.performance_degradation === null
                          ? "Not assessed"
                          : m.performance_degradation
                            ? "Review recommended"
                            : "Not detected"}
                      </td>
                      <td>
                        <Badge value={m.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="info-note">
              {live.data.limitations} Investigator dispositions are not verified
              labels.
            </p>
          </>
        )}
      </Panel>
      <State
        loading={drift.isLoading}
        error={drift.error}
        retry={() => drift.refetch()}
      />
      {drift.data && (
        <>
          <div className="health-strip">
            <div>
              <strong>Distribution status</strong>
              <Badge value={drift.data.status} />
            </div>
            <div>
              <strong>Reference records</strong>
              {number(drift.data.reference_count)}
            </div>
            <div>
              <strong>Current records</strong>
              {number(drift.data.current_count)}
            </div>
          </div>
          <Panel title="Feature distribution monitoring">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>PSI</th>
                    <th>KS statistic</th>
                    <th>KS p-value</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {drift.data.features.map((f) => (
                    <tr key={f.feature}>
                      <td>{f.feature}</td>
                      <td>{number(f.psi)}</td>
                      <td>{number(f.ks_statistic)}</td>
                      <td>{number(f.p_value)}</td>
                      <td>
                        <Badge value={f.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="info-note">
              {drift.data.limitations} {drift.data.recommendation}
            </p>
          </Panel>
        </>
      )}
      <div className="grid-main">
        <Panel title="Persisted drift investigations">
          <State
            loading={incidents.isLoading}
            error={incidents.error}
            retry={() => incidents.refetch()}
            empty={incidents.data?.items.length === 0}
          />
          {incidents.data?.items.map((i) => (
            <div className="model-card" key={i.id}>
              <div>
                <button className="text-link" onClick={() => setSelected(i.id)}>
                  {i.title}
                </button>
                <Badge value={i.status} />
              </div>
              <p>{i.summary}</p>
              <small>
                {date(i.created_at)} · {i.created_by} · {i.severity}
              </small>
            </div>
          ))}
        </Panel>
        {canInvestigate && (
          <Panel title="Open a drift investigation">
            <label>
              Title
              <input
                minLength={5}
                maxLength={180}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            </label>
            <label>
              Investigation summary
              <textarea
                minLength={10}
                maxLength={4000}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
              />
            </label>
            <label>
              Severity
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
              >
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </label>
            <p className="muted">
              Opening an investigation persists the server's current drift
              report. Model promotion is a separate reviewed action.
            </p>
            <button
              className="primary"
              disabled={
                title.trim().length < 5 ||
                summary.trim().length < 10 ||
                create.isPending
              }
              onClick={() => create.mutate()}
            >
              Capture report & open investigation
            </button>
            {create.error && (
              <p className="error" role="alert">
                {create.error.message}
              </p>
            )}
          </Panel>
        )}
      </div>
      {selected !== null && (
        <IncidentDetail
          id={selected}
          canEdit={canInvestigate}
          close={() => setSelected(null)}
        />
      )}
      {role === "administrator" && <VerifiedLabelForm />}
    </>
  );
}
function IncidentDetail({
  id,
  canEdit,
  close,
}: {
  id: number;
  canEdit: boolean;
  close: () => void;
}) {
  const client = useQueryClient();
  const q = useQuery({
    queryKey: ["incident", id],
    queryFn: () => api<DriftIncident>(`/monitoring/incidents/${id}`),
  });
  const [note, setNote] = useState("");
  const [status, setStatus] = useState("Investigating");
  const [confirmed, setConfirmed] = useState(false);
  const update = useMutation({
    mutationFn: () =>
      api(`/monitoring/incidents/${id}/events`, { note, status, confirmed }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["incident", id] });
      client.invalidateQueries({ queryKey: ["incidents"] });
      setNote("");
      setConfirmed(false);
    },
  });
  return (
    <Panel
      title={q.data?.title || "Drift investigation"}
      action={<button onClick={close}>Close details</button>}
    >
      <State loading={q.isLoading} error={q.error} retry={() => q.refetch()} />
      {q.data && (
        <>
          <p>{q.data.summary}</p>
          <div className="health-strip">
            <div>
              <strong>Stored report status</strong>
              <Badge value={q.data.report.status} />
            </div>
            <div>Captured {date(q.data.created_at)}</div>
            <div>
              Reference {number(q.data.report.reference_count)} · Current{" "}
              {number(q.data.report.current_count)}
            </div>
          </div>
          <div className="timeline">
            {q.data.history?.map((h) => (
              <article key={h.id}>
                <span />
                <strong>{h.status}</strong>
                <small>
                  {date(h.created_at)} · {h.actor}
                </small>
                <p>{h.note}</p>
              </article>
            ))}
          </div>
          {canEdit && q.data.status !== "Resolved" && (
            <>
              <label>
                Investigation update
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  maxLength={4000}
                />
              </label>
              <label>
                Next status
                <select
                  value={status}
                  onChange={(e) => {
                    setStatus(e.target.value);
                    setConfirmed(false);
                  }}
                >
                  <option>Open</option>
                  <option>Investigating</option>
                  <option>Resolved</option>
                </select>
              </label>
              {status === "Resolved" && (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={confirmed}
                    onChange={(e) => setConfirmed(e.target.checked)}
                  />
                  I confirm resolution; this investigation will become
                  immutable.
                </label>
              )}
              <button
                className="primary"
                disabled={
                  note.trim().length < 5 ||
                  update.isPending ||
                  (status === "Resolved" && !confirmed)
                }
                onClick={() => update.mutate()}
              >
                Record investigation update
              </button>
              {update.error && (
                <p className="error" role="alert">
                  {update.error.message}
                </p>
              )}
            </>
          )}
        </>
      )}
    </Panel>
  );
}
function VerifiedLabelForm() {
  const client = useQueryClient();
  const [id, setId] = useState("");
  const [label, setLabel] = useState(0);
  const [source, setSource] = useState("");
  const [evidence, setEvidence] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const submit = useMutation({
    mutationFn: () =>
      api<{ accepted: number; duplicates: number }>(
        "/monitoring/verified-labels",
        {
          labels: [
            {
              transaction_id: id,
              label,
              source,
              evidence,
              verified_at: new Date().toISOString(),
            },
          ],
        },
      ),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["live-performance"] });
      setConfirmed(false);
    },
  });
  return (
    <Panel
      title="Register an independent verified outcome"
      eyebrow="ADMINISTRATOR · SYNTHETIC DEMONSTRATION"
    >
      <p className="muted">
        Use independent evidence, not a risk score or initial investigator
        opinion. This record does not overwrite the generated benchmark label.
      </p>
      <div className="form-grid">
        <label>
          Transaction ID
          <input value={id} onChange={(e) => setId(e.target.value)} />
        </label>
        <label>
          Verified outcome
          <select
            value={label}
            onChange={(e) => setLabel(Number(e.target.value))}
          >
            <option value={0}>Legitimate (0)</option>
            <option value={1}>Fraud (1)</option>
          </select>
        </label>
        <label>
          Evidence source
          <input value={source} onChange={(e) => setSource(e.target.value)} />
        </label>
      </div>
      <label>
        Independent evidence
        <textarea
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
          maxLength={4000}
        />
      </label>
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={confirmed}
          onChange={(e) => setConfirmed(e.target.checked)}
        />
        I confirm this outcome has independent supporting evidence.
      </label>
      <button
        className="primary"
        disabled={
          !id.trim() ||
          source.trim().length < 3 ||
          evidence.trim().length < 10 ||
          !confirmed ||
          submit.isPending
        }
        onClick={() => submit.mutate()}
      >
        Register verified outcome
      </button>
      {submit.error && (
        <p className="error" role="alert">
          {submit.error.message}
        </p>
      )}
      {submit.data && (
        <p role="status">
          Accepted {submit.data.accepted}; duplicate records{" "}
          {submit.data.duplicates}.
        </p>
      )}
    </Panel>
  );
}
