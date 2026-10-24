import type {
  User,
  Page,
  Transaction,
  Case,
  Dashboard,
  Explanation,
  Evaluation as EvaluationData,
  Metrics,
  Drift,
  Model,
  PipelineRun,
  Performance,
} from "../types/api";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
  LineChart,
  Line,
} from "recharts";
import {
  ArrowUpRight,
  Search,
  ArrowLeft,
  ArrowRight,
  Download,
  RefreshCw,
} from "lucide-react";
import { api, number, percent, date } from "../api/client";
import { Panel, Badge, State, Metric } from "../components/UI";
const riskColor = (band: string) =>
  ({
    low: "#257b69",
    moderate: "#d9ad4e",
    high: "#e48b59",
    critical: "#ca5b5b",
  })[band.toLowerCase()] || "#83977b";
function Heading({
  eyebrow,
  title,
  text,
  children,
}: {
  eyebrow: string;
  title: string;
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{text}</p>
      </div>
      {children}
    </div>
  );
}
function useData<T>(path: string) {
  return useQuery({
    queryKey: [path],
    queryFn: () => api<T>(path),
    refetchInterval: path === "/pipeline/runs" ? 5000 : false,
  });
}
function TxTable({
  items,
  open,
}: {
  items: Transaction[];
  open: (id: string) => void;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Transaction / account</th>
            <th>Amount</th>
            <th>Channel</th>
            <th>Risk score</th>
            <th>Status</th>
            <th>Timestamp</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((t) => (
            <tr key={t.transaction_id}>
              <td>
                <button
                  className="text-link mono"
                  onClick={() => open(t.transaction_id)}
                >
                  {t.transaction_id}
                </button>
                <small>{t.account_id}</small>
              </td>
              <td className="amount">
                {t.currency} {number(t.amount)}
              </td>
              <td>{t.channel}</td>
              <td>
                <div className="risk-inline">
                  <b>{number(t.risk_score)}</b>
                  <Badge value={t.risk_band} />
                </div>
              </td>
              <td>
                <Badge value={t.status} />
              </td>
              <td>{date(t.timestamp)}</td>
              <td>
                <button
                  className="icon-button"
                  aria-label={`Inspect ${t.transaction_id}`}
                  onClick={() => open(t.transaction_id)}
                >
                  <ArrowUpRight size={17} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function Overview({
  open,
  go,
}: {
  open: (id: string) => void;
  go: (p: string) => void;
}) {
  const q = useData<Dashboard>("/dashboard");
  const d = q.data;
  return (
    <>
      <Heading
        eyebrow="RISK INTELLIGENCE"
        title="A clearer view of risk."
        text="Understand the signals. Focus your investigations where they matter."
      >
        <button onClick={() => q.refetch()}>
          <RefreshCw size={15} />
          Refresh data
        </button>
      </Heading>
      <State loading={q.isLoading} error={q.error} retry={() => q.refetch()} />
      {d && (
        <>
          <div className="metrics">
            <Metric
              label="Transactions processed"
              value={number(d.transactions)}
              detail="Validated synthetic transactions"
            />
            <Metric
              label="Alerts generated"
              value={number(d.alerts)}
              detail={`${number(d.open_cases)} investigations open`}
            />
            <Metric
              label="High & critical risk"
              value={number(d.high_risk)}
              detail="Prioritized for human review"
              accent
            />
            <Metric
              label="False-positive rate"
              value={percent(d.false_positive_rate)}
              detail="Held-out synthetic evaluation"
            />
          </div>
          <div className="grid-main">
            <Panel
              title="Transaction activity"
              eyebrow="SIGNALS OVER TIME"
              action={
                <span className="legend">
                  <i />
                  Transactions <i className="gold" />
                  Alerts
                </span>
              }
            >
              <div className="chart">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={d.trend}>
                    <defs>
                      <linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="0%"
                          stopColor="#4e9d89"
                          stopOpacity={0.26}
                        />
                        <stop
                          offset="100%"
                          stopColor="#4e9d89"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid vertical={false} stroke="#edf0ec" />
                    <XAxis
                      dataKey="date"
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis
                      tickLine={false}
                      axisLine={false}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip />
                    <Area
                      isAnimationActive={false}
                      type="monotone"
                      dataKey="transactions"
                      stroke="#287f6c"
                      strokeWidth={2.5}
                      fill="url(#fill)"
                    />
                    <Area
                      isAnimationActive={false}
                      type="monotone"
                      dataKey="alerts"
                      stroke="#c69b46"
                      fill="transparent"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="panel-caption">
                Actual daily transaction and alert counts from your database.
              </div>
            </Panel>
            <Panel title="Risk distribution" eyebrow="CURRENT PORTFOLIO">
              <div className="risk-bars">
                {[...(d.risk_distribution || [])]
                  .sort(
                    (a, b) =>
                      ["low", "moderate", "high", "critical"].indexOf(
                        a.band.toLowerCase(),
                      ) -
                      ["low", "moderate", "high", "critical"].indexOf(
                        b.band.toLowerCase(),
                      ),
                  )
                  .map((r) => (
                    <div key={r.band}>
                      <div>
                        <span>
                          <i style={{ background: riskColor(r.band) }} />
                          {r.band}
                        </span>
                        <strong>{number(r.count)}</strong>
                      </div>
                      <div className="track">
                        <span
                          style={{
                            width: `${(100 * r.count) / Math.max(d.transactions, 1)}%`,
                            background: riskColor(r.band),
                          }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
              <div className="info-note">
                Risk bands indicate review priority, not confirmed fraud.
              </div>
            </Panel>
          </div>
          <div className="health-strip">
            <div>
              <span className="status-dot" />
              <strong>Pipeline</strong>
              <Badge value={d.pipeline_health} />
            </div>
            <div>
              <strong>Drift status</strong>
              <Badge value={d.drift_status} />
            </div>
            <div>
              <strong>Active model</strong>
              <span className="mono">{d.model_version || "Not trained"}</span>
            </div>
            <div>
              <strong>Labelled fraud prevalence</strong>
              {percent(d.fraud_rate)}
            </div>
          </div>
          <Panel
            title="Investigation queue"
            eyebrow="RECENT ALERTS"
            action={
              <button className="text-link" onClick={() => go("cases")}>
                View investigations <ArrowRight size={14} />
              </button>
            }
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Transaction</th>
                    <th>Risk score</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Created</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {(d.recent_alerts || []).map((a) => (
                    <tr key={a.id}>
                      <td className="mono">{a.transaction_id}</td>
                      <td>
                        <strong>{number(a.risk_score)}</strong>
                        <div className="score-track">
                          <i style={{ width: `${a.risk_score}%` }} />
                        </div>
                      </td>
                      <td>
                        <Badge value={a.risk_band} />
                      </td>
                      <td>
                        <Badge value={a.status} />
                      </td>
                      <td>{date(a.created_at)}</td>
                      <td>
                        <button
                          className="text-link"
                          onClick={() => open(a.transaction_id)}
                        >
                          Investigate <ArrowUpRight size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <State empty={!d.recent_alerts?.length} />
          </Panel>
        </>
      )}
    </>
  );
}
export function Transactions({
  selected,
  open,
  close,
}: {
  selected: string | null;
  open: (id: string) => void;
  close: () => void;
}) {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [band, setBand] = useState("");
  const [channel, setChannel] = useState("");
  const [amount, setAmount] = useState("");
  const [sort, setSort] = useState("timestamp");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [status, setStatus] = useState("");
  const params = new URLSearchParams({
    page: String(page),
    page_size: "15",
    search,
    risk_band: band,
    channel,
    min_amount: amount,
    sort,
    order: "desc",
    date_from: from,
    date_to: to ? to + "T23:59:59Z" : "",
    status,
  });
  for (const [key, value] of [...params.entries()])
    if (!value) params.delete(key);
  const q = useData<Page<Transaction>>(`/transactions?${params}`);
  if (selected)
    return <TransactionDetail id={selected} close={close} open={open} />;
  return (
    <>
      <Heading
        eyebrow="TRANSACTION EXPLORER"
        title="Follow the money. Find the context."
        text="Inspect transaction activity and the model signals behind each prediction."
      />
      <Panel
        title="All transactions"
        action={<span className="count">{number(q.data?.total)} records</span>}
      >
        <div className="filters">
          <label className="search">
            <Search size={16} />
            <input
              aria-label="Search transaction ID"
              placeholder="Search transaction ID…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </label>
          <select
            aria-label="Risk band"
            value={band}
            onChange={(e) => {
              setBand(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All risk bands</option>
            {["Low", "Moderate", "High", "Critical"].map((v) => (
              <option key={v}>{v}</option>
            ))}
          </select>
          <input
            aria-label="Channel filter"
            placeholder="Filter channel"
            value={channel}
            onChange={(e) => {
              setChannel(e.target.value);
              setPage(1);
            }}
          />
          <input
            aria-label="Minimum amount"
            type="number"
            min="0"
            placeholder="Minimum amount"
            value={amount}
            onChange={(e) => {
              setAmount(e.target.value);
              setPage(1);
            }}
          />
          <select
            aria-label="Sort by"
            value={sort}
            onChange={(e) => setSort(e.target.value)}
          >
            <option value="timestamp">Newest first</option>
            <option value="risk_score">Highest risk</option>
            <option value="amount">Largest amount</option>
          </select>
          <input
            aria-label="From date"
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setPage(1);
            }}
          />
          <input
            aria-label="To date"
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setPage(1);
            }}
          />
          <select
            aria-label="Transaction status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            {["New", "Assigned", "Under Review", "Escalated", "Resolved"].map(
              (v) => (
                <option key={v}>{v}</option>
              ),
            )}
          </select>
        </div>
        <State
          loading={q.isLoading}
          error={q.error}
          retry={() => q.refetch()}
          empty={q.data?.items?.length === 0}
        />
        {q.data?.items && <TxTable items={q.data.items} open={open} />}
        <div className="pagination">
          <span>
            Page {page} · {number(q.data?.total)} results
          </span>
          <div>
            <button disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
              Previous
            </button>
            <button
              disabled={!q.data || page * 15 >= q.data.total}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </Panel>
    </>
  );
}
function TransactionDetail({
  id,
  close,
  open,
}: {
  id: string;
  close: () => void;
  open: (id: string) => void;
}) {
  const q = useData<Transaction>(`/transactions/${id}`);
  const exp = useData<Explanation>(`/transactions/${id}/explanation`);
  const d = q.data;
  const e = exp.data;
  const contributors = e?.contributions || [];
  return (
    <>
      <button className="text-link back" onClick={close}>
        <ArrowLeft size={16} />
        Back to transactions
      </button>
      <Heading
        eyebrow="EXPLAINABLE INVESTIGATION"
        title="The story behind the score."
        text={id}
      />
      <State loading={q.isLoading} error={q.error} retry={() => q.refetch()} />
      {d && (
        <>
          <div className="metrics">
            <Metric
              label="Transaction amount"
              value={`${d.currency} ${number(d.amount)}`}
              detail={d.merchant_category || d.transaction_type}
            />
            <Metric
              label="Operational risk"
              value={`${number(d.prediction?.risk_score)} / 100`}
              detail={d.prediction?.risk_band || "Not scored"}
              accent
            />
            <Metric
              label="Fraud probability"
              value={percent(d.prediction?.fraud_probability)}
              detail="Supervised model output"
            />
            <Metric
              label="Model version"
              value={
                <span className="version">{d.prediction?.model_version}</span>
              }
              detail={date(d.prediction?.prediction_timestamp || d.timestamp)}
            />
          </div>
          <div className="health-strip">
            <div>
              <strong>Anomaly percentile</strong>
              {percent(d.prediction?.anomaly_score)}
            </div>
            <div>
              <strong>Rule score</strong>
              {number(d.prediction?.rule_score)} / 100
            </div>
            <div>Operational score = 100 × logistic probability</div>
          </div>
          <div className="grid-main">
            <Panel
              title="What influenced this prediction?"
              eyebrow="MODEL ATTRIBUTION"
            >
              <State
                loading={exp.isLoading}
                error={exp.error}
                retry={() => exp.refetch()}
              />
              {e && (
                <>
                  <p className="chart-description">
                    {e.method} · contributions in{" "}
                    {e.units || "model output units"}
                  </p>
                  <div className="chart contributions">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={contributors}
                        layout="vertical"
                        margin={{ left: 15, right: 20 }}
                      >
                        <CartesianGrid horizontal={false} stroke="#edf0ec" />
                        <XAxis type="number" tick={{ fontSize: 11 }} />
                        <YAxis
                          dataKey="feature"
                          type="category"
                          width={150}
                          tick={{ fontSize: 11 }}
                        />
                        <Tooltip />
                        <ReferenceLine x={0} stroke="#9ba8a0" />
                        <Bar
                          dataKey="contribution"
                          radius={3}
                          isAnimationActive={false}
                        >
                          {contributors.map((r, i: number) => (
                            <Cell
                              key={i}
                              fill={r.contribution > 0 ? "#d78064" : "#378b76"}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="explanation-equation">
                    Baseline {number(e.baseline)} + contributions ={" "}
                    {number(e.output_log_odds)} <span>{e.units}</span>
                  </div>
                  <p className="info-note">
                    {e.limitations ||
                      "Attribution explains model behavior, not causation or criminal intent."}
                  </p>
                </>
              )}
            </Panel>
            <Panel title="Transaction context" eyebrow="SOURCE RECORD">
              <dl>
                {[
                  ["Account", d.account_id],
                  ["Customer", d.customer_id],
                  ["Channel", d.channel],
                  ["Country", d.country_code],
                  ["Merchant", d.merchant_id],
                  ["Device", d.device_id],
                  ["Occurred", date(d.timestamp)],
                ].map(([k, v]) => (
                  <div key={k}>
                    <dt>{k}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
              <div className="info-note">
                An unusual transaction may be legitimate. Review the surrounding
                activity before recording a decision.
              </div>
            </Panel>
          </div>
          {e && (
            <Panel title="Feature evidence">
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Feature</th>
                      <th>Observed value</th>
                      <th>Baseline</th>
                      <th>Contribution</th>
                      <th>Meaning</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contributors.map((c) => (
                      <tr key={c.feature}>
                        <td>{c.feature}</td>
                        <td>{number(c.value)}</td>
                        <td>{number(c.baseline)}</td>
                        <td className={c.contribution > 0 ? "error" : "green"}>
                          {number(c.contribution)}
                        </td>
                        <td>{c.description || c.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="panel-caption">
                Triggered rules:{" "}
                {(d.prediction?.triggered_rules || [])
                  .map((r) => (typeof r === "string" ? r : r.name || r.rule))
                  .join(", ") || "None"}
              </p>
            </Panel>
          )}
          <Panel title="Related account activity">
            <TxTable items={d.related_transactions || []} open={open} />
            <State empty={!d.related_transactions?.length} />
          </Panel>
        </>
      )}
    </>
  );
}
export function Investigation({ open }: { open: (id: string) => void }) {
  const [selected, setSelected] = useState<number | null>(null);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState("");
  const list = useData<Page<Case>>(
    `/cases?page=${page}&page_size=50&status=${status}&search=${encodeURIComponent(search)}&risk_band=${risk}`,
  );
  return (
    <>
      <Heading
        eyebrow="HUMAN-IN-THE-LOOP"
        title="Turn signals into informed decisions."
        text="Assign, review and resolve alerts with a complete audit trail."
      />
      {selected ? (
        <>
          <button className="text-link back" onClick={() => setSelected(null)}>
            <ArrowLeft size={16} />
            Back to queue
          </button>
          <CaseDetail id={selected} open={open} />
        </>
      ) : (
        <Panel
          title="Investigation queue"
          action={
            <select
              aria-label="Case status"
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {["New", "Assigned", "Under Review", "Escalated", "Resolved"].map(
                (s) => (
                  <option key={s}>{s}</option>
                ),
              )}
            </select>
          }
        >
          <div className="filters">
            <input
              aria-label="Search cases"
              placeholder="Search transaction ID…"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
            <select
              aria-label="Case risk band"
              value={risk}
              onChange={(e) => {
                setRisk(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All risk bands</option>
              {["low", "moderate", "high", "critical"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </div>
          <State
            loading={list.isLoading}
            error={list.error}
            retry={() => list.refetch()}
            empty={list.data?.items?.length === 0}
          />
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Transaction</th>
                  <th>Risk</th>
                  <th>Status</th>
                  <th>Assignee</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {list.data?.items?.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <button
                        className="text-link"
                        onClick={() => setSelected(c.id)}
                      >
                        CASE-{c.id} <ArrowUpRight size={13} />
                      </button>
                    </td>
                    <td className="mono">{c.transaction_id}</td>
                    <td>
                      <Badge value={c.risk_band} /> {number(c.risk_score)}
                    </td>
                    <td>
                      <Badge value={c.status} />
                    </td>
                    <td>{c.assigned_to || "Unassigned"}</td>
                    <td>{date(c.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>
              Page {page} · {number(list.data?.total)} cases
            </span>
            <div>
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <button
                disabled={!list.data || page * 50 >= list.data.total}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </Panel>
      )}
    </>
  );
}
function CaseDetail({ id, open }: { id: number; open: (id: string) => void }) {
  const q = useData<Case>(`/alerts/${id}`);
  const users = useData<User[]>("/users");
  const client = useQueryClient();
  const [note, setNote] = useState("");
  const [assignee, setAssignee] = useState("");
  const [disposition, setDisposition] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [reason, setReason] = useState("");
  const mutation = useMutation({
    mutationFn: ({ action, body }: { action: string; body: unknown }) =>
      api(`/alerts/${id}/${action}`, body),
    onSuccess: (_, variables) => {
      client.invalidateQueries();
      if (variables.action === "notes") setNote("");
      setConfirm(false);
    },
  });
  const d = q.data;
  return (
    <>
      <State loading={q.isLoading} error={q.error} retry={() => q.refetch()} />
      {d && (
        <div className="grid-main">
          <Panel title={`Case ${id}`} action={<Badge value={d.status} />}>
            <div className="case-summary">
              <strong className="mono">{d.transaction_id}</strong>
              <Badge value={d.risk_band} />
              <button
                className="text-link"
                onClick={() => open(d.transaction_id)}
              >
                Inspect explanation <ArrowUpRight size={15} />
              </button>
            </div>
            <label>
              Assign investigator
              <div className="inline-form">
                <select
                  aria-label="Assign investigator"
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                >
                  <option value="">Select investigator</option>
                  {(users.data || []).map((u) => (
                    <option key={u.id} value={u.username}>
                      {u.username} · {u.role}
                    </option>
                  ))}
                </select>
                <button
                  disabled={!assignee || mutation.isPending}
                  onClick={() =>
                    mutation.mutate({
                      action: "assign",
                      body: { username: assignee },
                    })
                  }
                >
                  Assign
                </button>
                <button
                  disabled={
                    mutation.isPending ||
                    !["Assigned", "assigned"].includes(d.status)
                  }
                  onClick={() =>
                    mutation.mutate({
                      action: "status",
                      body: { status: "Under Review" },
                    })
                  }
                >
                  Start review
                </button>
              </div>
            </label>
            <label>
              Investigation note
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Document the evidence and your reasoning…"
                maxLength={5000}
              />
            </label>
            <button
              className="primary"
              disabled={!note.trim() || mutation.isPending}
              onClick={() =>
                mutation.mutate({ action: "notes", body: { text: note } })
              }
            >
              Add note
            </button>
            <div className="notes">
              {d.notes?.map((n) => (
                <article key={n.id}>
                  <div>
                    <strong>{n.author || n.username}</strong>
                    <small>{date(n.created_at)}</small>
                  </div>
                  <p>{n.text}</p>
                </article>
              ))}
            </div>
            <hr />
            <label>
              Escalation reason
              <div className="inline-form">
                <input
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Why is additional review needed?"
                />
                <button
                  disabled={
                    !reason.trim() ||
                    mutation.isPending ||
                    d.status === "Resolved"
                  }
                  onClick={() =>
                    mutation.mutate({ action: "escalate", body: { reason } })
                  }
                >
                  Escalate
                </button>
              </div>
            </label>
            <label>
              Record a disposition
              <select
                value={disposition}
                onChange={(e) => {
                  setDisposition(e.target.value);
                  setConfirm(false);
                }}
              >
                <option value="">Select outcome</option>
                {[
                  "Confirmed suspicious activity",
                  "Legitimate activity / false positive",
                  "Inconclusive",
                  "Requires further review",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </label>
            <p className="muted">
              Investigator opinion remains separate from the synthetic
              ground-truth label.
            </p>
            {confirm ? (
              <div className="confirmation">
                <strong>Resolve this case as “{disposition}”?</strong>
                <p>This decision will be recorded in the audit trail.</p>
                <button
                  className="primary"
                  onClick={() =>
                    mutation.mutate({
                      action: "disposition",
                      body: { disposition, confirmed: true },
                    })
                  }
                  disabled={mutation.isPending}
                >
                  Confirm decision
                </button>
                <button onClick={() => setConfirm(false)}>Cancel</button>
              </div>
            ) : (
              <button
                disabled={
                  !disposition || mutation.isPending || d.status === "Resolved"
                }
                onClick={() => setConfirm(true)}
              >
                Review & resolve
              </button>
            )}
            {mutation.isError && (
              <p className="error" role="alert">
                {mutation.error.message}
              </p>
            )}
            {mutation.isSuccess && (
              <p className="green" role="status">
                Case updated and audit event recorded.
              </p>
            )}
          </Panel>
          <Panel title="Audit trail" eyebrow="ACCOUNTABLE BY DESIGN">
            <div className="timeline">
              {d.history?.map((h, i: number) => (
                <article key={h.id || i}>
                  <span />
                  <strong>{h.action?.replaceAll("_", " ")}</strong>
                  <small>
                    {date(h.created_at)} · {h.actor || h.username}
                  </small>
                  <p>
                    {typeof h.details === "string"
                      ? h.details
                      : JSON.stringify(h.details)}
                  </p>
                </article>
              ))}
            </div>
            <State empty={!d.history?.length} />
          </Panel>
        </div>
      )}
    </>
  );
}
function exportJSON(data: unknown, name: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}
export function Evaluation() {
  const [threshold, setThreshold] = useState(50);
  const q = useData<EvaluationData>(
    `/evaluation/metrics?threshold=${threshold / 100}`,
  );
  const curves = useData<Metrics[]>("/evaluation/thresholds");
  const d = q.data;
  const rows = d?.models || [];
  const metrics = d;
  return (
    <>
      <Heading
        eyebrow="SYNTHETIC BENCHMARK"
        title="Measure what matters."
        text="Precision, recall and review workload on chronologically held-out data."
      >
        <button disabled={!d} onClick={() => exportJSON(d, "evaluation.json")}>
          <Download size={15} />
          Export report
        </button>
      </Heading>
      <Panel
        title="Decision threshold"
        action={<strong>{threshold} / 100</strong>}
      >
        <p className="chart-description">
          Explore the trade-off between missed fraud and investigation workload.
          This control analyzes held-out predictions; it does not change live
          alert policy.
        </p>
        <input
          className="threshold"
          aria-label="Evaluation threshold"
          type="range"
          min="0"
          max="100"
          step="5"
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
        />
        <div className="range-labels">
          <span>More alerts · greater sensitivity</span>
          <span>Fewer alerts · higher selectivity</span>
        </div>
      </Panel>
      <State loading={q.isLoading} error={q.error} retry={() => q.refetch()} />
      {metrics && (
        <>
          <div className="metrics">
            <Metric
              label="Precision"
              value={percent(metrics.precision)}
              detail="True positives / all alerts"
            />
            <Metric
              label="Recall"
              value={percent(metrics.recall)}
              detail="Detected / labelled fraud"
            />
            <Metric
              label="F1 score"
              value={number(metrics.f1)}
              detail="Precision–recall balance"
            />
            <Metric
              label="Alert volume"
              value={number(metrics.alert_volume)}
              detail="At selected threshold"
              accent
            />
          </div>
          <div className="grid-main">
            <Panel title="Threshold trade-offs">
              <div className="chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={curves.data || []}>
                    <CartesianGrid vertical={false} stroke="#edf0ec" />
                    <XAxis dataKey="threshold" />
                    <YAxis domain={[0, 1]} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="precision"
                      stroke="#267e6a"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="recall"
                      stroke="#d39a4f"
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="legend panel-caption">
                <i />
                Precision <i className="gold" />
                Recall
              </div>
            </Panel>
            <Panel title="Confusion matrix">
              <div className="confusion">
                <div>
                  <span>True positives</span>
                  <strong>{number(metrics.true_positives)}</strong>
                </div>
                <div>
                  <span>False positives</span>
                  <strong>{number(metrics.false_positives)}</strong>
                </div>
                <div>
                  <span>False negatives</span>
                  <strong>{number(metrics.false_negatives)}</strong>
                </div>
                <div>
                  <span>True negatives</span>
                  <strong>{number(metrics.true_negatives)}</strong>
                </div>
              </div>
              <p className="info-note">
                Positive class: synthetic fraud label = 1. Unknown labels are
                excluded.
              </p>
            </Panel>
          </div>
          <div className="grid-main">
            <Panel title="Precision–recall curve">
              <div className="chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={d?.curves?.precision_recall || []}>
                    <CartesianGrid stroke="#edf0ec" />
                    <XAxis
                      dataKey="recall"
                      type="number"
                      domain={[0, 1]}
                      label={{
                        value: "Recall",
                        position: "insideBottomRight",
                        offset: -4,
                      }}
                    />
                    <YAxis domain={[0, 1]} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="precision"
                      stroke="#267e6a"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>
            <Panel title="ROC curve">
              <div className="chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={d?.curves?.roc || []}>
                    <CartesianGrid stroke="#edf0ec" />
                    <XAxis
                      dataKey="false_positive_rate"
                      type="number"
                      domain={[0, 1]}
                    />
                    <YAxis domain={[0, 1]} />
                    <Tooltip />
                    <Line
                      dataKey="true_positive_rate"
                      stroke="#b49b52"
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Panel>
          </div>
          <Panel title="Detection by synthetic scenario">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Scenario</th>
                    <th>Test records</th>
                    <th>Detection rate</th>
                  </tr>
                </thead>
                <tbody>
                  {(d?.by_scenario || []).map((r) => (
                    <tr key={r.scenario}>
                      <td>{r.scenario.replaceAll("_", " ")}</td>
                      <td>{number(r.sample_count)}</td>
                      <td>{percent(r.detection_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <Panel title="Model comparison">
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1</th>
                    <th>PR-AUC</th>
                    <th>ROC-AUC</th>
                    <th>False-positive rate</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((m) => (
                    <tr key={m.name}>
                      <td>{m.name}</td>
                      <td>{percent(m.precision)}</td>
                      <td>{percent(m.recall)}</td>
                      <td>{number(m.f1)}</td>
                      <td>{number(m.pr_auc)}</td>
                      <td>{number(m.roc_auc)}</td>
                      <td>{percent(m.false_positive_rate)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <State empty={!rows.length} />
            <p className="info-note">
              Synthetic benchmark results do not establish real-world banking
              performance. Anomaly rank is not a calibrated fraud probability.
            </p>
          </Panel>
        </>
      )}
    </>
  );
}
export function Administration({ role }: { role?: string }) {
  const [promotion, setPromotion] = useState<string | null>(null);
  const activation = useMutation({
    mutationFn: (version: string) =>
      api("/models/" + encodeURIComponent(version) + "/activate", {}),
    onSuccess: () => {
      client.invalidateQueries();
      setPromotion(null);
    },
  });
  const runs = useData<Page<PipelineRun>>("/pipeline/runs");
  const models = useData<Model[]>("/models");
  const client = useQueryClient();
  const [count, setCount] = useState(3000);
  const [seed, setSeed] = useState(42);
  const [prevalence, setPrevalence] = useState(0.06);
  const run = useMutation({
    mutationFn: () =>
      api("/pipeline/runs", {
        transactions: count,
        seed,
        customers: 180,
        fraud_rate: prevalence,
      }),
    onSuccess: () => client.invalidateQueries(),
  });
  const items = models.data || [];
  return (
    <>
      <Heading
        eyebrow="DATA OPERATIONS"
        title="Reproducible from the first record."
        text="Generate synthetic data, inspect pipeline runs and track registered models."
      />
      <div className="grid-main">
        <Panel
          title="Generate & score a dataset"
          eyebrow="DETERMINISTIC PIPELINE"
        >
          <div className="form-grid">
            <label>
              Transactions
              <input
                type="number"
                min="500"
                max="100000"
                value={count}
                onChange={(e) => setCount(Number(e.target.value))}
              />
            </label>
            <label>
              Random seed
              <input
                type="number"
                min="0"
                value={seed}
                onChange={(e) => setSeed(Number(e.target.value))}
              />
            </label>
            <label>
              Fraud prevalence
              <input
                type="number"
                min="0.005"
                max="0.3"
                step="0.01"
                value={prevalence}
                onChange={(e) => setPrevalence(Number(e.target.value))}
              />
            </label>
          </div>
          <p className="muted">
            Generation, validation, chronological features, model training and
            batch scoring run together. Larger datasets take longer.
          </p>
          <button
            className="primary"
            disabled={
              role !== "administrator" ||
              run.isPending ||
              count < 500 ||
              count > 100000 ||
              prevalence < 0.005 ||
              prevalence > 0.3
            }
            onClick={() => run.mutate()}
          >
            {run.isPending ? "Pipeline running…" : "Run synthetic pipeline"}{" "}
            <ArrowRight size={15} />
          </button>
          {role !== "administrator" && (
            <p className="muted">
              Administrator access is required to start pipeline runs.
            </p>
          )}
          {run.isError && (
            <p className="error" role="alert">
              {run.error.message}
            </p>
          )}
          {run.isSuccess && (
            <p className="green">
              Pipeline request completed. Inspect its recorded status below.
            </p>
          )}
        </Panel>
        <Panel title="Registered models" eyebrow="VERSIONED ARTIFACTS">
          <State
            loading={models.isLoading}
            error={models.error}
            retry={() => models.refetch()}
            empty={!models.isLoading && !items.length}
          />
          {items.map((m) => (
            <div className="model-card" key={m.version || m.model_version}>
              <div>
                <strong className="mono">{m.version || m.model_version}</strong>
                <Badge
                  value={m.status || (m.active ? "Active" : "Registered")}
                />
              </div>
              <p>{m.info?.algorithm || m.algorithm || "Registered model"}</p>
              <small>{date(m.created_at)}</small>
              {role === "administrator" && !m.active && (
                <div className="model-action">
                  {promotion === m.version ? (
                    <>
                      <p className="muted">
                        Activate this model for future scoring? Existing
                        predictions retain their original model versions.
                      </p>
                      <button
                        className="primary"
                        disabled={activation.isPending}
                        onClick={() => activation.mutate(m.version)}
                      >
                        Confirm activation
                      </button>
                      <button onClick={() => setPromotion(null)}>Cancel</button>
                    </>
                  ) : (
                    <button onClick={() => setPromotion(m.version)}>
                      Review activation
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
          {activation.isError && (
            <p className="error">{activation.error.message}</p>
          )}
        </Panel>
      </div>
      <Panel title="Pipeline execution history">
        <State
          loading={runs.isLoading}
          error={runs.error}
          retry={() => runs.refetch()}
        />
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Processed</th>
                <th>Rejected</th>
                <th>Duration</th>
                <th>Started</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {(runs.data?.items || []).map((r) => (
                <tr key={r.id}>
                  <td className="mono">{r.id}</td>
                  <td>
                    <Badge value={r.status} />
                  </td>
                  <td>{number(r.processed)}</td>
                  <td>{number(r.rejected)}</td>
                  <td>{number(r.duration_seconds)}s</td>
                  <td>{date(r.started_at || r.created_at)}</td>
                  <td>{r.error || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}
