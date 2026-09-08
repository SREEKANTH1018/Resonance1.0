import React, { useEffect, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, ArrowLeft, BarChart3, CheckCircle2, ChevronRight,
  ClipboardCheck, Database, FileSearch, Gauge, History, Image, LayoutDashboard,
  Link2, Menu, RefreshCw, Search, Send, ShieldCheck, Sparkles, X, Zap
} from "lucide-react";
import { api, pretty, pick, API_BASE } from "./api";

const nav = [
  ["dashboard", "Dashboard", LayoutDashboard],
  ["decisions", "Decisions", Database],
  ["verify", "Verify", ShieldCheck],
  ["create", "New Decision", Sparkles]
];

function App() {
  const [page, setPage] = useState("dashboard");
  const [selectedId, setSelectedId] = useState(null);
  const [mobileOpen, setMobileOpen] = useState(false);

  const openDecision = (id) => {
    setSelectedId(id);
    setPage("detail");
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={22}/></div>
          <div><strong>ARGUS</strong><span>Decision Ledger</span></div>
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([key, label, Icon]) => (
            <button key={key} className={page === key ? "nav-item active" : "nav-item"}
              onClick={() => { setPage(key); setMobileOpen(false); }}>
              <Icon size={18}/><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <BackendStatus/>
          <div className="tiny">AI models stay behind the FastAPI boundary.<br/>Provider secrets belong on the server.</div>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <button className="icon-btn mobile-menu" onClick={() => setMobileOpen(v => !v)}><Menu size={20}/></button>
          <div>
            <div className="eyebrow">PS19 • ARGUS</div>
            <h1>{page === "detail" ? "Decision Detail" : nav.find(n => n[0] === page)?.[1] || "ARGUS Ledger"}</h1>
          </div>
          <div className="top-actions">
            <span className="api-pill"><span className="dot"/> API: {API_BASE.replace(/^https?:\/\//, "")}</span>
            <button className="icon-btn" title="Refresh" onClick={() => window.dispatchEvent(new Event("argus-refresh"))}><RefreshCw size={18}/></button>
          </div>
        </header>

        <section className="content">
          {page === "dashboard" && <Dashboard onOpen={openDecision} onNew={() => setPage("create")}/>}
          {page === "decisions" && <Decisions onOpen={openDecision} onNew={() => setPage("create")}/>}
          {page === "detail" && <DecisionDetail id={selectedId} onBack={() => setPage("decisions")}/>}
          {page === "create" && <DecisionCreator onCreated={openDecision}/>}
          {page === "verify" && <Verifier onCreated={openDecision}/>}
        </section>
      </main>
    </div>
  );
}

function BackendStatus() {
  const [state, setState] = useState("checking");
  useEffect(() => {
    let alive = true;
    const check = () => api.health().then(() => alive && setState("online")).catch(() => alive && setState("offline"));
    check();
    const timer = setInterval(check, 15000);
    return () => { alive = false; clearInterval(timer); };
  }, []);
  return <div className="status-card">
    <div className={`status-icon ${state}`}><Activity size={17}/></div>
    <div><b>Backend</b><span>{state === "online" ? "Connected" : state === "offline" ? "Unavailable" : "Checking…"}</span></div>
  </div>;
}

function Dashboard({onOpen, onNew}) {
  const [data, setData] = useState(null);
  const [decisions, setDecisions] = useState([]);
  const [error, setError] = useState("");

  const load = async () => {
    setError("");
    try {
      const [d, list] = await Promise.all([api.dashboard(), api.decisions()]);
      setData(d);
      setDecisions(Array.isArray(list) ? list : (list?.items || list?.decisions || []));
    } catch(e) { setError(e.message); }
  };
  useEffect(() => { load(); const h = () => load(); window.addEventListener("argus-refresh", h); return () => window.removeEventListener("argus-refresh", h); }, []);

  const stats = useMemo(() => {
    const source = data || {};
    return [
      ["Total Decisions", pick(source, ["total_decisions","decisions_count","total"], decisions.length), Database],
      ["Needs Review", pick(source, ["pending_human_review","pending_reviews","human_review_count","needs_review"], "—"), ClipboardCheck],
      ["Avg Trust Score", formatConfidence(pick(source, ["average_trust_score","average_confidence","avg_confidence"], "—")), Gauge],
      ["High Risk", pick(source, ["high_risk_decisions","high_risk"], "—"), AlertTriangle]
    ];
  }, [data, decisions]);

  return <div className="stack">
    {error && <ErrorBox message={error}/>}
    <div className="hero">
      <div><span className="kicker"><Zap size={14}/> Audit-grade AI decisions</span>
        <h2>See what the AI decided,<br/><em>and why.</em></h2>
        <p>ARGUS connects decisions, evidence, resource usage and append-only audit events through your FastAPI backend.</p>
      </div>
      <button className="primary" onClick={onNew}><Sparkles size={17}/> Generate decision</button>
    </div>
    <div className="stats-grid">
      {stats.map(([label,value,Icon]) => <div className="stat-card" key={label}><div className="stat-icon"><Icon size={18}/></div><span>{label}</span><strong>{value}</strong></div>)}
    </div>
    <Panel title="Recent decisions" action={<button className="text-btn" onClick={() => onOpen(decisions[0]?.id)} disabled={!decisions[0]}>Open latest <ChevronRight size={15}/></button>}>
      {decisions.length ? <DecisionTable rows={decisions.slice(0,8)} onOpen={onOpen}/> : <EmptyState title="No decisions yet" text="Create or generate your first decision to populate the ledger."/>}
    </Panel>
  </div>;
}

function Decisions({onOpen,onNew}) {
  const [rows,setRows] = useState([]);
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState("");
  const load = () => { setLoading(true); api.decisions().then(d => setRows(Array.isArray(d) ? d : (d?.items || d?.decisions || []))).catch(e=>setError(e.message)).finally(()=>setLoading(false)); };
  useEffect(()=>{load(); const h=()=>load(); window.addEventListener("argus-refresh",h); return ()=>window.removeEventListener("argus-refresh",h)},[]);
  return <div className="stack">
    <div className="page-intro"><div><div className="kicker">LEDGER</div><h2>All decisions</h2><p>Every persisted AI decision exposed by the backend.</p></div><button className="primary" onClick={onNew}><Sparkles size={17}/> New decision</button></div>
    {error && <ErrorBox message={error}/>}
    <Panel title={`${rows.length} loaded`} action={<button className="icon-btn" onClick={load}><RefreshCw size={17}/></button>}>
      {loading ? <Loader/> : rows.length ? <DecisionTable rows={rows} onOpen={onOpen}/> : <EmptyState title="Ledger is empty" text="Use New Decision or Generate Decision to add data."/>}
    </Panel>
  </div>;
}

function DecisionTable({rows,onOpen}) {
  return <div className="table-wrap"><table><thead><tr><th>Decision</th><th>Confidence</th><th>Status</th><th>Created</th><th></th></tr></thead><tbody>
    {rows.map((r,i) => {
      const id = pick(r,["id","decision_id"],null);
      const conf = pick(r,["confidence","confidence_score"],null);
      return <tr key={id || i} onClick={()=>id && onOpen(id)}>
        <td><div className="decision-cell"><span className="decision-bullet">{String(i+1).padStart(2,"0")}</span><div><b>{pick(r,["title","decision_type","type"],"AI Decision")}</b><small>{id || "No ID"}</small></div></div></td>
        <td>{formatConfidence(conf)}</td>
        <td><Status value={pick(r,["status","decision_status"],"RECORDED")}/></td>
        <td>{formatDate(pick(r,["created_at","timestamp","created"],null))}</td>
        <td><ChevronRight size={16}/></td>
      </tr>
    })}</tbody></table></div>;
}

function DecisionDetail({id,onBack}) {
  const [data,setData]=useState(null), [evidence,setEvidence]=useState([]), [audit,setAudit]=useState([]), [error,setError]=useState(""), [tab,setTab]=useState("overview");
  const [reviewOpen,setReviewOpen]=useState(false);
  const load=async()=>{ if(!id)return; setError(""); try { const [d,e,a]=await Promise.all([api.decision(id),api.evidence(id),api.audit(id)]); setData(d); setEvidence(Array.isArray(e)?e:(e?.items||e?.evidence||[])); setAudit(Array.isArray(a)?a:(a?.items||a?.events||a?.audit||[])); } catch(e){setError(e.message)} };
  useEffect(()=>{load()},[id]);
  if(!id) return <EmptyState title="No decision selected" text="Return to the decisions list." action={onBack}/>;
  return <div className="stack">
    <button className="back-btn" onClick={onBack}><ArrowLeft size={16}/> Back to decisions</button>
    {error && <ErrorBox message={error}/>}
    {!data ? <Loader/> : <>
      <div className="detail-head">
        <div><div className="kicker">DECISION {id}</div><h2>{pick(data,["title","decision_type","type"],"AI Decision")}</h2><p>{pick(data,["created_at","timestamp"],"")}</p></div>
        <div className="detail-actions"><Status value={pick(data,["status","decision_status"],"RECORDED")}/><button className="secondary" onClick={()=>setReviewOpen(true)}><ClipboardCheck size={16}/> Human review</button></div>
      </div>
      <div className="detail-tabs">{["overview","evidence","audit","raw"].map(t=><button className={tab===t?"tab active":"tab"} onClick={()=>setTab(t)} key={t}>{t}</button>)}</div>
      {tab==="overview" && <Overview data={data}/>}
      {tab==="evidence" && <Evidence rows={evidence}/>}
      {tab==="audit" && <Audit rows={audit}/>}
      {tab==="raw" && <pre className="json-view">{pretty(data)}</pre>}
    </>}
    {reviewOpen && <ReviewModal id={id} onClose={()=>setReviewOpen(false)} onDone={()=>{setReviewOpen(false);load()}}/>}
  </div>;
}

function Overview({data}) {
  const confidence = pick(data,["confidence","confidence_score"],null);
  return <div className="detail-grid">
    <Panel title="AI assessment"><div className="assessment"><div className="confidence-ring"><strong>{formatConfidence(confidence)}</strong><span>confidence</span></div><div><h3>{pick(data,["decision","prediction","label","result"],"Decision recorded")}</h3><p>{pick(data,["rationale","reason","explanation","summary"],null) || (Array.isArray(data?.reasons) && data.reasons.length ? data.reasons.join(" • ") : "No explanation field was returned by the API.")}</p></div></div></Panel>
    <Panel title="Decision metadata"><Meta data={data}/></Panel>
    <Panel title="Evidence" action={<span className="panel-count"><FileSearch size={15}/></span>}><NestedList value={pick(data,["evidence","evidence_items"],null)}/></Panel>
    <Panel title="Resource usage"><NestedList value={pick(data,["resource_usage","resources"],null)}/></Panel>
  </div>;
}

function Evidence({rows}) {
  return <Panel title="Supporting evidence">{rows.length?<div className="evidence-list">{rows.map((r,i)=><div className="evidence-card" key={i}><div className="evidence-top"><span className="source-num">{i+1}</span><div><b>{pick(r,["title","source_name","name"],"Evidence")}</b><small>{pick(r,["url","source_url","source"],"")}</small></div><span className="score">{formatConfidence(pick(r,["score","relevance_score","confidence"],null))}</span></div><p>{pick(r,["snippet","content","text","description"],"No evidence text returned.")}</p></div>)}</div>:<EmptyState title="No evidence rows" text="This decision has no evidence records returned by the backend."/>}</Panel>;
}

function Audit({rows}) {
  return <Panel title="Append-only audit history">{rows.length?<div className="timeline">{rows.map((r,i)=><div className="timeline-item" key={i}><div className="timeline-dot"><History size={13}/></div><div><b>{pick(r,["event_type","type","action","event"],"EVENT")}</b><small>{formatDate(pick(r,["created_at","timestamp","occurred_at"],null))}</small><p>{pick(r,["message","description","details"],"")}</p></div></div>)}</div>:<EmptyState title="No audit events" text="No audit events were returned for this decision."/>}</Panel>;
}

const PERSIST_TEMPLATE = JSON.stringify({
  input_text: "Applicant meets all documented eligibility criteria; risk score below threshold.",
  decision: "APPROVED",
  confidence: 0.91,
  reasons: ["Eligibility satisfied", "Risk below threshold"],
  evidence: [{ source: "policy.pdf", page: 4, content: "Eligibility clause is met.", relevance: 0.96, reason: "Primary basis" }],
  model: "Model-A",
  model_version: "1.2",
  policy_name: "Policy-01",
  policy_version: "3.1"
}, null, 2);

function DecisionCreator({onCreated}) {
  const [mode,setMode]=useState("generate"), [text,setText]=useState("Assess this input and return an auditable AI decision."), [json,setJson]=useState(PERSIST_TEMPLATE), [loading,setLoading]=useState(false), [error,setError]=useState("");
  const submit=async()=>{setLoading(true);setError("");try{
    let payload, result;
    if(mode==="generate"){
      // POST /decisions/generate — backend contract: { input_text, policy_name?, policy_version? }
      payload={ input_text: text.trim() || "Assess this input and return an auditable AI decision." };
      result=await api.generateDecision(payload);
    } else {
      // POST /decisions — backend contract: app/schemas.py::DecisionCreate
      payload=JSON.parse(json);
      result=await api.createDecision(payload);
    }
    const id=pick(result,["decision_id","id"],null) || pick(result?.decision,["decision_id","id"],null);
    if(id) onCreated(id); else alert("Request succeeded. The backend response did not expose an ID, so the raw response is shown below.\\n\\n"+pretty(result));
  }catch(e){setError(e.message)}finally{setLoading(false)}};
  return <div className="stack">
    <div className="page-intro"><div><div className="kicker">INGEST</div><h2>Create a ledger record</h2><p>Use the backend's generate path for AI output, or persist a decision produced by another engine.</p></div></div>
    <div className="creator-grid">
      <Panel title="Request"><div className="segmented"><button className={mode==="generate"?"selected":""} onClick={()=>setMode("generate")}><Sparkles size={15}/> AI Generate</button><button className={mode==="persist"?"selected":""} onClick={()=>setMode("persist")}><Database size={15}/> Persist decision</button></div>
      {mode==="generate"
        ? <label>Input / prompt <span className="hint">Sent as <code>{`{ input_text }`}</code> to POST /decisions/generate.</span><textarea value={text} onChange={e=>setText(e.target.value)} rows={6}/></label>
        : <label>JSON payload <span className="hint">Body for POST /decisions — matches app/schemas.py::DecisionCreate.</span><textarea className="code-input" value={json} onChange={e=>setJson(e.target.value)} rows={16}/></label>}
      {error && <ErrorBox message={error}/>}
      <button className="primary wide" onClick={submit} disabled={loading}>{loading?<><Spinner/> Sending…</>:<><Send size={16}/> Send to FastAPI</>}</button>
      </Panel>
      <Panel title="Integration flow"><FlowStep n="01" title="Frontend" text="Collects input and sends JSON only."/><FlowStep n="02" title="FastAPI" text="Owns validation, AI provider calls and persistence."/><FlowStep n="03" title="AI engine" text="Your teammate's trained service can sit behind the backend integration layer."/><FlowStep n="04" title="PostgreSQL" text="Stores the decision, evidence, resources and audit history."/></Panel>
    </div>
  </div>;
}

function Verifier() {
  const [kind,setKind]=useState("text"), [text,setText]=useState(""), [url,setUrl]=useState(""), [file,setFile]=useState(null), [result,setResult]=useState(null), [error,setError]=useState(""), [loading,setLoading]=useState(false);
  const submit=async()=>{setLoading(true);setError("");setResult(null);try{let r;if(kind==="text")r=await api.verifyText({text});if(kind==="url")r=await api.verifyUrl({url});if(kind==="image")r=await api.verifyImage(file,{text});setResult(r)}catch(e){setError(e.message)}finally{setLoading(false)}};
  return <div className="stack">
    <div className="page-intro"><div><div className="kicker">AI VERIFICATION</div><h2>Verify evidence</h2><p>Frontend adapter for the optional verification routes. Provider credentials stay on the backend.</p></div></div>
    <div className="verify-grid">
      <Panel title="Verification input"><div className="segmented">{[["text","Text",FileSearch],["url","URL",Link2],["image","Image",Image]].map(([k,l,I])=><button key={k} className={kind===k?"selected":""} onClick={()=>setKind(k)}><I size={15}/>{l}</button>)}</div>
      {kind==="text" && <label>Claim / text<textarea rows={8} value={text} onChange={e=>setText(e.target.value)} placeholder="Paste the claim you want ARGUS to assess…"/></label>}
      {kind==="url" && <label>URL<input value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://example.com/article"/></label>}
      {kind==="image" && <><label>Image<input type="file" accept="image/*" onChange={e=>setFile(e.target.files?.[0]||null)}/></label><label>Optional context<textarea rows={4} value={text} onChange={e=>setText(e.target.value)}/></label></>}
      {error && <ErrorBox message={error}/>}
      <button className="primary wide" onClick={submit} disabled={loading || (kind==="image"&&!file)}>{loading?<><Spinner/> Verifying…</>:<><ShieldCheck size={16}/> Run verification</>}</button>
    </Panel>
    <Panel title="Result">{result?<ResultView result={result}/>:<EmptyState title="No result yet" text="Submit text, a URL, or an image to see the backend response."/>}</Panel>
    </div>
  </div>;
}

function ResultView({result}) {
  const confidence=pick(result,["confidence","verification_confidence","assessment_confidence"],null);
  const warnings=Array.isArray(result?.warnings)?result.warnings:[];
  const engines=result?.engines&&typeof result.engines==="object"?Object.keys(result.engines):[];
  return <div className="result"><div className="result-banner"><div><span>ASSESSMENT</span><strong>{pick(result,["status","result","label"],"COMPLETED")}</strong></div><div className="result-confidence">{formatConfidence(confidence)}</div></div>
    {warnings.length>0 && <div className="result-section"><h4>Warnings — providers not yet connected</h4><ul className="nested-list">{warnings.map((w,i)=><li key={i}>{String(w)}</li>)}</ul></div>}
    {engines.length>0 && <div className="result-section"><h4>Engine output</h4><NestedList value={result.engines}/></div>}
    <div className="result-section"><h4>Claims</h4><NestedList value={pick(result,["claims"],null)}/></div><div className="result-section"><h4>Sources</h4><NestedList value={pick(result,["sources"],null)}/></div><details><summary>Raw response</summary><pre className="json-view compact">{pretty(result)}</pre></details></div>;
}

function ReviewModal({id,onClose,onDone}) {
  const [payload,setPayload]=useState('{\n  "reviewer": "analyst.jordan",\n  "decision": "APPROVED",\n  "reason": "Manual override after reviewing the evidence."\n}'),[loading,setLoading]=useState(false),[error,setError]=useState("");
  const submit=async()=>{setLoading(true);setError("");try{await api.reviewDecision(id,JSON.parse(payload));onDone()}catch(e){setError(e.message)}finally{setLoading(false)}};
  return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><div className="modal"><div className="modal-head"><h3>Human review</h3><button className="icon-btn" onClick={onClose}><X size={18}/></button></div><p>Submit the review payload to the backend. Keep reviewer identity and policy decisions on the server.</p><textarea className="code-input" rows={12} value={payload} onChange={e=>setPayload(e.target.value)}/>{error&&<ErrorBox message={error}/>}<div className="modal-actions"><button className="secondary" onClick={onClose}>Cancel</button><button className="primary" onClick={submit} disabled={loading}>{loading?"Saving…":"Save review"}</button></div></div></div>;
}

function Meta({data}) {
  const skip=["evidence","evidence_items","resource_usage","resources","audit","events","rationale","reason","explanation"];
  const entries=Object.entries(data||{}).filter(([k])=>!skip.includes(k) && typeof data[k]!=="object");
  return <div className="meta-grid">{entries.slice(0,12).map(([k,v])=><div key={k}><span>{k.replaceAll("_"," ")}</span><b>{String(v)}</b></div>)}</div>;
}
function NestedList({value}) { if(value===null||value===undefined) return <div className="muted">No data returned.</div>; if(Array.isArray(value)) return value.length?<ul className="nested-list">{value.slice(0,12).map((x,i)=><li key={i}>{typeof x==="object"?<pre>{pretty(x)}</pre>:String(x)}</li>)}</ul>:<div className="muted">Empty.</div>; return <pre className="nested-pre">{pretty(value)}</pre>; }
function FlowStep({n,title,text}) { return <div className="flow-step"><span>{n}</span><div><b>{title}</b><p>{text}</p></div></div>; }
function Panel({title,action,children}) { return <div className="panel"><div className="panel-head"><h3>{title}</h3>{action}</div>{children}</div>; }
function Status({value}) { const v=String(value||"").toUpperCase(); const type=v.includes("REVIEW")||v.includes("PENDING")?"warn":v.includes("REJECT")||v.includes("FAIL")||v.includes("FALSE")?"bad":"good"; return <span className={`status ${type}`}><span/> {value}</span>; }
function ErrorBox({message}) { return <div className="error-box"><AlertTriangle size={17}/><div><b>Backend request failed</b><pre>{message}</pre></div></div>; }
function EmptyState({title,text,action}) { return <div className="empty"><div className="empty-icon"><Database size={19}/></div><h3>{title}</h3><p>{text}</p>{action&&<button className="secondary" onClick={action}>Go back</button>}</div>; }
function Loader(){return <div className="loader"><Spinner/> Loading from FastAPI…</div>}
function Spinner(){return <span className="spinner"/>}
function formatDate(v){if(!v)return "—";const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleString();}
function formatConfidence(v){if(v===null||v===undefined||v==="—")return "—";const n=Number(v);if(Number.isNaN(n))return String(v);return `${(n<=1?n*100:n).toFixed(0)}%`}

export default App;