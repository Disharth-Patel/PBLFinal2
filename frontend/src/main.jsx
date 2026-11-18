import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { ArrowRight, Bell, Bot, BookOpen, CheckCircle2, GraduationCap, LayoutDashboard, LogOut, MessageCircle, Mic, Send, ShieldCheck, Sparkles, Users } from "lucide-react";
import "./styles.css";
import "./admin.css";

const API = "http://127.0.0.1:8000/api/v1";
const request = async (path, options = {}) => {
  const response = await fetch(API + path, { headers: { "Content-Type": "application/json", ...(localStorage.token ? { Authorization: `Bearer ${localStorage.token}` } : {}), ...options.headers }, ...options });
  const body = await response.json();
  if (response.status === 401 && localStorage.token) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    window.location.reload();
    throw new Error("Your session expired. Please sign in again.");
  }
  if (!response.ok) throw new Error(body.detail || "Request failed");
  return body;
};

function App() {
  const [user, setUser] = useState(JSON.parse(localStorage.user || "null"));
  const [authMode, setAuthMode] = useState(null);
  const [page, setPage] = useState("home");
  const signOut = () => { localStorage.clear(); setUser(null); setPage("home"); };
  if (user) return <Dashboard user={user} page={page} setPage={setPage} signOut={signOut} />;
  return <><Header onLogin={() => setAuthMode("login")} onRegister={() => setAuthMode("register")} /><Landing onStart={() => setAuthMode("register")} />{authMode && <Auth mode={authMode} setMode={setAuthMode} onSuccess={(value) => { setUser(value); setPage("chat"); }} />}</>;
}

function Header({ onLogin, onRegister }) {
  return <header className="header"><div className="brand"><div className="brand-mark"><Sparkles size={18} /></div><span>MIT ADT <b>Admissions AI</b></span></div><nav><a href="#how">How it works</a><a href="#features">Features</a><button className="link-button" onClick={onLogin}>Sign in</button><button className="button small" onClick={onRegister}>Get started <ArrowRight size={15} /></button></nav></header>;
}

function Landing({ onStart }) {
  return <main><section className="hero"><div className="hero-copy"><div className="eyebrow"><span className="pulse" /> LOCAL-FIRST ADMISSIONS INTELLIGENCE</div><h1>Your next chapter<br /><em>starts here.</em></h1><p>Get clear, grounded answers about programmes, eligibility and admissions — powered by your institution's verified knowledge.</p><div className="hero-actions"><button className="button" onClick={onStart}>Talk to the assistant <ArrowRight size={17} /></button><span className="trust"><ShieldCheck size={18} /> Private. Local. Verified.</span></div></div><div className="hero-card"><div className="orb"><Bot size={42} /></div><div className="mini-label">AI ADMISSIONS ASSISTANT</div><h3>How can I help<br />you today?</h3><div className="suggestion">What programmes are available? <ArrowRight size={14} /></div><div className="suggestion">How do I apply? <ArrowRight size={14} /></div><div className="card-glow" /></div></section><section id="features" className="feature-section"><div className="section-intro"><span className="eyebrow">ONE CONVERSATION AWAY</span><h2>Admissions guidance,<br /><em>without the guesswork.</em></h2></div><div className="features"><Feature icon={<BookOpen />} title="Grounded in your institution" text="Answers come from your official brochures and contact directory — never invented." /><Feature icon={<MessageCircle />} title="Built for real questions" text="Ask about programmes, fees, eligibility or next steps in natural language." /><Feature icon={<Mic />} title="Text or voice" text="Have a conversation your way with local voice capabilities when configured." /></div></section></main>;
}

function Feature({ icon, title, text }) { return <article className="feature"><div className="feature-icon">{icon}</div><h3>{title}</h3><p>{text}</p></article>; }

function Auth({ mode, setMode, onSuccess }) {
  const [form, setForm] = useState({ name: "", email: "", password: "" }); const [error, setError] = useState("");
  const submit = async (event) => { event.preventDefault(); try { const data = await request(`/auth/${mode}`, { method: "POST", body: JSON.stringify(form) }); localStorage.token = data.token; localStorage.user = JSON.stringify(data.user); onSuccess(data.user); } catch (e) { setError(e.message); } };
  return <div className="modal-backdrop"><form className="modal" onSubmit={submit}><button type="button" className="close" onClick={() => setMode(null)}>×</button><span className="eyebrow">{mode === "login" ? "WELCOME BACK" : "START YOUR JOURNEY"}</span><h2>{mode === "login" ? "Sign in to continue." : "Create your account."}</h2>{mode === "register" && <input placeholder="Full name" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />}<input type="email" placeholder="Email address" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /><input type="password" placeholder="Password (8+ characters)" required minLength="8" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} />{error && <div className="error">{error}</div>}<button className="button">{mode === "login" ? "Sign in" : "Create account"} <ArrowRight size={16} /></button><button type="button" className="link-button" onClick={() => setMode(mode === "login" ? "register" : "login")}>{mode === "login" ? "Need an account? Register" : "Already registered? Sign in"}</button></form></div>;
}

function Dashboard({ user, page, setPage, signOut }) {
  return <div className="app-shell"><aside><div className="brand"><div className="brand-mark"><Sparkles size={18} /></div><span>ADT <b>Admissions AI</b></span></div><div className="side-label">WORKSPACE</div><SideButton active={page === "overview"} onClick={() => setPage("overview")} icon={<LayoutDashboard />} text="Overview" /> <SideButton active={page === "chat"} onClick={() => setPage("chat")} icon={<MessageCircle />} text="AI Assistant" />{user.role !== "admin" && <SideButton active={page === "leads"} onClick={() => setPage("leads")} icon={<Users />} text="My enquiry" />} <SideButton active={page === "profile"} onClick={() => setPage("profile")} icon={<GraduationCap />} text="My profile" />{user.role === "admin" && <><div className="side-label">ADMIN</div><SideButton active={page === "admin"} onClick={() => setPage("admin")} icon={<ShieldCheck />} text="Admin overview" /><SideButton active={page === "review-enquiries"} onClick={() => setPage("review-enquiries")} icon={<Users />} text="Review enquiries" /></>}<button className="logout" onClick={signOut}><LogOut size={17} /> Sign out</button></aside><div className="dashboard-main"><div className="topbar"><span className="status"><span className="pulse" /> Local AI connected</span><Notifications /><div className="avatar">{user.name[0]}</div></div>{page === "chat" ? <Chat user={user} /> : page === "admin" || page === "review-enquiries" ? <Admin /> : page === "leads" && user.role !== "admin" ? <LeadForm /> : page === "profile" ? <Profile /> : <Overview user={user} setPage={setPage} />}</div></div>;
}
function SideButton({ active, onClick, icon, text }) { return <button className={`side-button ${active ? "active" : ""}`} onClick={onClick}>{icon}{text}</button>; }
function Notifications() {
  const [items, setItems] = useState([]);
  useEffect(() => { request("/notifications").then(setItems).catch(() => {}); }, []);
  const unread = items.filter(item => !item.read).length;
  return <div className="notifications" title={unread ? `${unread} unread notifications` : "No new notifications"}><Bell size={18} />{unread > 0 && <span>{unread}</span>}</div>;
}
function Overview({ user, setPage }) { return <section className="content"><div className="welcome"><div><span className="eyebrow">STUDENT DASHBOARD</span><h1>Good to see you, {user.name.split(" ")[0]}.</h1><p>Your admission journey starts with a good question.</p></div><button className="button" onClick={() => setPage("chat")}>Ask the assistant <ArrowRight size={16} /></button></div><div className="overview-grid"><div className="stat-card dark"><Sparkles /><span>AI assistant</span><strong>Ready to help</strong><small>Grounded in official sources</small></div><div className="stat-card"><CheckCircle2 /><span>Knowledge base</span><strong>Verified sources</strong><small>Institutional information</small></div><div className="stat-card"><GraduationCap /><span>Next step</span><strong>Tell us your goals</strong><small>We personalise your guidance</small></div></div><div className="tip"><Sparkles /><div><b>Start with anything.</b><p>Try asking “Which programmes are available in design?” or “What documents do I need?”</p></div></div></section>; }
function Chat() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([{ role: "assistant", content: "Hi! I’m your MIT ADT admissions assistant. Ask me about programmes, eligibility, application steps or anything else on your mind." }]);
  const [conversationId, setConversationId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [voiceMessage, setVoiceMessage] = useState("");
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const [history, setHistory] = useState([]);
  useEffect(() => { request("/conversations").then(setHistory).catch(() => {}); }, []);
  useEffect(() => () => recognitionRef.current?.abort(), []);
  const send = async (event) => { event.preventDefault(); if (!input.trim() || busy) return; const text = input; setInput(""); setMessages(m => [...m, { role: "user", content: text }]); setBusy(true); try { const result = await request("/chat", { method: "POST", body: JSON.stringify({ conversation_id: conversationId, message: text }) }); setConversationId(result.conversation_id); setMessages(m => [...m, { role: "assistant", content: result.answer, sources: result.sources }]); } catch (e) { setMessages(m => [...m, { role: "assistant", content: `I couldn't reach the local assistant: ${e.message}` }]); } finally { setBusy(false); } };
  const toggleBrowserSpeech = () => {
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setVoiceMessage("Browser speech-to-text is not supported in this browser. You can continue typing.");
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = navigator.language || "en-IN";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognition.onstart = () => { setListening(true); setVoiceMessage("Listening…"); };
    recognition.onresult = event => {
      const transcript = Array.from(event.results)
        .slice(event.resultIndex)
        .map(result => result[0].transcript)
        .join(" ");
      if (transcript.trim()) setInput(previous => `${previous} ${transcript}`.trim());
    };
    recognition.onerror = event => {
      setListening(false);
      setVoiceMessage(event.error === "not-allowed" ? "Microphone access was denied. Allow microphone access for this site and try again." : `Speech recognition failed: ${event.error}.`);
    };
    recognition.onend = () => { setListening(false); recognitionRef.current = null; };
    recognitionRef.current = recognition;
    recognition.start();
  };
  const loadConversation = async (id) => { const rows = await request(`/conversations/${id}/messages`); setConversationId(id); setMessages(rows); };
  const removeConversation = async (id) => { await request(`/conversations/${id}`, { method: "DELETE" }); setHistory(rows => rows.filter(row => row.id !== id)); if (conversationId === id) { setConversationId(null); setMessages([]); } };
  return <section className="chat-page"><div className="chat-heading"><div><span className="eyebrow">AI ADMISSIONS ASSISTANT</span><h1>What would you like to know?</h1></div><button className="outline-button" onClick={() => { setMessages([]); setConversationId(null); }}>New conversation</button></div><div className="conversation-history">{history.slice(0, 5).map(row => <div className="history-item" key={row.id}><button onClick={() => loadConversation(row.id)}>{row.title}</button><button className="history-delete" onClick={() => removeConversation(row.id)}>×</button></div>)}</div><div className="chat-window">{messages.map((m, i) => <div key={i} className={`message-row ${m.role}`}><div className="message-avatar">{m.role === "assistant" ? <Bot size={16} /> : "You"}</div><div className="message"><p>{m.content}</p>{m.sources?.length > 0 && <small>Sources: {m.sources.map(s => `${s.source} (${s.location})`).join(", ")}</small>}</div></div>)}{busy && <div className="typing">Local assistant is thinking…</div>}</div><form className="chat-input" onSubmit={send}><input value={input} onChange={e => setInput(e.target.value)} placeholder="Ask about admissions, programmes, eligibility…" /><button type="button" className={`voice-button ${listening ? "listening" : ""}`} onClick={toggleBrowserSpeech} aria-label={listening ? "Stop speech-to-text" : "Start speech-to-text"} aria-pressed={listening}><Mic size={19} /></button><button className="send-button"><Send size={18} /></button></form>{voiceMessage && <div className="typing">{voiceMessage}</div>}</section>;
}
function LeadForm() { const [form, setForm] = useState({ programme: "", academic_qualification: "", notes: "" }); const [leads, setLeads] = useState([]); const [done, setDone] = useState(false); useEffect(() => { request("/leads").then(setLeads).catch(() => {}); }, []); const submit = async e => { e.preventDefault(); const result = await request("/leads", { method: "POST", body: JSON.stringify(form) }); setLeads(rows => [{ ...form, ...result, created_at: new Date().toISOString() }, ...rows]); setDone(true); }; return <section className="content narrow"><span className="eyebrow">ADMISSION ENQUIRY</span><h1>Keep the conversation going.</h1><p className="lede">Share a few details and an admissions counsellor can follow up with you.</p>{done ? <div className="success"><CheckCircle2 /><h3>Enquiry received</h3><p>Your details have been securely saved.</p></div> : <form className="lead-form" onSubmit={submit}><label>Programme of interest<input required value={form.programme} onChange={e => setForm({ ...form, programme: e.target.value })} placeholder="e.g. Computer Science" /></label><label>Academic qualification<input value={form.academic_qualification} onChange={e => setForm({ ...form, academic_qualification: e.target.value })} placeholder="e.g. 12th standard / Bachelor's" /></label><label>Anything else? <textarea value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} rows="4" /></label><button className="button">Submit enquiry <ArrowRight size={16} /></button></form>}<div className="panel"><div className="panel-heading"><h3>My enquiry history</h3><span>{leads.length} records</span></div>{leads.map(lead => <div className="audit-row" key={lead.id}><b>{lead.programme || "Programme not specified"}</b><span>{lead.status}</span><small>{new Date(lead.created_at).toLocaleString()}</small></div>)}</div></section>; }
function Profile() {
  const [form, setForm] = useState({ phone: "", academic_qualification: "", interested_programme: "", preferred_department: "", admission_year: "", communication_language: "English", interests: "" });
  const [saved, setSaved] = useState(false);
  useEffect(() => { request("/profile").then(profile => setForm(previous => ({ ...previous, ...profile }))).catch(() => {}); }, []);
  const save = async event => { event.preventDefault(); await request("/profile", { method: "PUT", body: JSON.stringify(form) }); if (form.interested_programme.trim()) await request("/course-interests", { method: "POST", body: JSON.stringify({ programme: form.interested_programme, department: form.preferred_department }) }); setSaved(true); };
  return <section className="content narrow"><span className="eyebrow">STUDENT PROFILE</span><h1>Personalise your guidance.</h1><p className="lede">Save your interests once so future admissions conversations can be more relevant.</p><form className="lead-form" onSubmit={save}>{[["phone","Phone number"],["academic_qualification","Academic qualification"],["interested_programme","Programme of interest"],["preferred_department","Preferred department"],["admission_year","Admission year"],["communication_language","Preferred language"],["interests","Additional interests"]].map(([key,label]) => <label key={key}>{label}{key === "interests" ? <textarea rows="3" value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} /> : <input value={form[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} />}</label>)}{saved && <div className="success">Profile saved.</div>}<button className="button">Save profile <CheckCircle2 size={16} /></button></form></section>; }
function Admin() {
  const [data, setData] = useState(null);
  const [leads, setLeads] = useState([]);
  const [logs, setLogs] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [escalations, setEscalations] = useState([]);
  const [followUps, setFollowUps] = useState([]);
  const [users, setUsers] = useState([]);
  const [activities, setActivities] = useState([]);
  const [courseInterests, setCourseInterests] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [enquirySearch, setEnquirySearch] = useState("");
  const [enquiryStatus, setEnquiryStatus] = useState("All");
  const [enquiryPage, setEnquiryPage] = useState(1);
  const [selectedEnquiry, setSelectedEnquiry] = useState(null);
  const [indexing, setIndexing] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [modelConfig, setModelConfig] = useState({ model_name: "qwen2.5:1.5b-instruct", temperature: 0.0, top_p: 1.0, context_length: 4096, max_tokens: 512 });
  const [models, setModels] = useState([]);
  const [message, setMessage] = useState("");
  const refresh = async () => {
    try {
      const [overview, leadRows, auditRows, config, ollama, documentRows, escalationRows, followUpRows, userRows, activityRows, interestRows, analyticsData] = await Promise.all([
        request("/admin/overview"),
        request("/admin/leads"),
        request("/admin/audit-logs"),
        request("/admin/model-configuration"),
        request("/ollama/status"),
        request("/admin/documents"),
        request("/admin/escalations"),
        request("/admin/follow-ups"),
        request("/admin/users"),
        request("/admin/activity"),
        request("/admin/course-interests"),
        request("/admin/analytics"),
      ]);
      setData(overview);
      setLeads(leadRows);
      setLogs(auditRows);
      setModelConfig(config);
      setModels(ollama.models || []);
      setDocuments(documentRows);
      setEscalations(escalationRows);
      setFollowUps(followUpRows);
      setUsers(userRows);
      setActivities(activityRows);
      setCourseInterests(interestRows);
      setAnalytics(analyticsData);
    } catch (error) {
      setMessage(error.message);
    }
  };
  useEffect(() => { refresh(); }, []);
  const indexKnowledge = async () => {
    if (indexing) return;
    setIndexing(true);
    setMessage("Indexing knowledge documents…");
    try {
      const result = await request("/knowledge/index", { method: "POST" });
      setMessage(`Knowledge indexed successfully: ${result.embedded} chunks are ready for retrieval.`);
      await refresh();
    } catch (error) { setMessage(error.message); }
    finally { setIndexing(false); }
  };
  const updateLead = async (lead, status) => {
    try {
      await request(`/admin/leads/${lead.id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      await refresh();
    } catch (error) { setMessage(error.message); }
  };
  const saveModel = async (event) => {
    event.preventDefault();
    try { await request("/admin/model-configuration", { method: "PUT", body: JSON.stringify(modelConfig) }); setMessage("Model configuration saved."); await refresh(); } catch (error) { setMessage(error.message); }
  };
  const uploadDocument = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${API}/admin/documents`, { method: "POST", headers: { Authorization: `Bearer ${localStorage.token}` }, body });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Upload failed");
      setMessage(`Uploaded ${result.filename}, version ${result.version}.`);
      await refresh();
    } catch (error) { setMessage(error.message); }
    event.target.value = "";
  };
  const updateEscalation = async (item, status) => {
    try { await request(`/admin/escalations/${item.id}`, { method: "PATCH", body: JSON.stringify({ status }) }); await refresh(); } catch (error) { setMessage(error.message); }
  };
  const updateFollowUp = async (item, status) => {
    try { await request(`/admin/follow-ups/${item.id}`, { method: "PATCH", body: JSON.stringify({ status }) }); await refresh(); } catch (error) { setMessage(error.message); }
  };
  const runDocumentOcr = async (document) => {
    try {
      const result = await request(`/admin/documents/${document.id}/ocr`, { method: "POST" });
      setMessage(`OCR extracted ${result.pages} pages from ${result.filename}. Re-index knowledge to include it.`);
      await refresh();
    } catch (error) { setMessage(error.message); }
  };
  const runEvaluation = async () => {
    if (evaluating) return;
    setEvaluating(true);
    setMessage("Preparing and running the knowledge evaluation…");
    try {
      await request("/admin/evaluation/dataset", { method: "POST" });
      const result = await request("/admin/evaluation/run", { method: "POST" });
      setEvaluation(result);
      setMessage(`Evaluation completed across ${result.cases} cases.`);
    } catch (error) { setMessage(error.message); }
    finally { setEvaluating(false); }
  };
  const exportLeads = async () => {
    const response = await fetch(`${API}/admin/leads/export`, { headers: { Authorization: "Bearer " + localStorage.token } });
    if (!response.ok) { setMessage("Lead export failed."); return; }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url; link.download = "admission-leads.csv"; link.click();
    URL.revokeObjectURL(url);
  };
  const filteredEnquiries = leads
    .filter(lead => enquiryStatus === "All" || lead.status === enquiryStatus)
    .filter(lead => `${lead.student_name} ${lead.student_email} ${lead.programme || ""} ${lead.notes || ""}`.toLowerCase().includes(enquirySearch.toLowerCase()));
  const enquiriesPerPage = 8;
  const pageCount = Math.max(1, Math.ceil(filteredEnquiries.length / enquiriesPerPage));
  const visibleEnquiries = filteredEnquiries.slice((enquiryPage - 1) * enquiriesPerPage, enquiryPage * enquiriesPerPage);
  return <section className="content">
    <div className="welcome"><div><span className="eyebrow">ADMINISTRATION</span><h1>System overview.</h1><p className="lede">Live operational signals from your admissions workspace.</p></div><div className="admin-actions"><label className="outline-button">Upload document<input type="file" hidden accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt" onChange={uploadDocument} /></label><button className="button" onClick={indexKnowledge} disabled={indexing}><BookOpen size={16} /> {indexing ? "Indexing…" : "Re-index knowledge"}</button></div></div>
    {message && <div className="tip"><ShieldCheck size={18} /><div>{message}</div></div>}
    <div className="overview-grid">{Object.entries(data || { students: "—", conversations: "—", leads: "—", indexed_documents: "—" }).filter(([key]) => ["total_registered_students", "active_students", "conversations", "total_admission_enquiries", "total_course_interests", "pending_enquiries", "converted_leads", "indexed_knowledge_documents"].includes(key)).map(([key, value]) => <div className="stat-card" key={key}><span>{key.replaceAll("_", " ")}</span><strong>{value}</strong><small>Current total</small></div>)}</div>
    <div className="panel analytics-panel"><div className="panel-heading"><h3>Analytics snapshot</h3><button className="outline-button" onClick={exportLeads}>Export leads CSV</button></div><div className="analytics-row"><span>Pending escalations <b>{analytics?.escalations_pending ?? "—"}</b></span><span>Lead statuses <b>{Object.keys(analytics?.lead_status || {}).length}</b></span><span>Programmes <b>{Object.keys(analytics?.programme || {}).length}</b></span><span>Feedback ratings <b>{Object.keys(analytics?.feedback || {}).length}</b></span></div></div>
    <div className="panel analytics-panel"><div className="panel-heading"><h3>Knowledge evaluation</h3><button className="outline-button" onClick={runEvaluation} disabled={evaluating}>{evaluating ? "Evaluating…" : "Run evaluation"}</button></div>{evaluation ? <div className="analytics-row"><span>Retrieval hit rate <b>{(evaluation.hit_rate * 100).toFixed(1)}%</b></span><span>Unavailable precision <b>{(evaluation.unavailable_precision * 100).toFixed(1)}%</b></span><span>Cases <b>{evaluation.cases}</b></span><small>{evaluation.report_path}</small></div> : <p className="lede">Run the evaluation to measure retrieval coverage and safe handling of unsupported questions.</p>}</div>
    <div className="panel enquiry-panel"><div className="panel-heading"><div><h3>Review enquiries</h3><p className="panel-subtitle">Enquiries submitted by users. Administrators can review details and update their status.</p></div><span>{filteredEnquiries.length} of {leads.length} records</span></div><div className="enquiry-filters"><input aria-label="Search enquiries" placeholder="Search customer, email, programme or notes" value={enquirySearch} onChange={event => { setEnquirySearch(event.target.value); setEnquiryPage(1); }} /><select aria-label="Filter enquiries by status" value={enquiryStatus} onChange={event => { setEnquiryStatus(event.target.value); setEnquiryPage(1); }}><option>All</option><option>New</option><option>Submitted</option><option>Contacted</option><option>Interested</option><option>Qualified</option><option>Follow-up Required</option><option>Escalated</option><option>Converted</option><option>Not Interested</option></select></div>{visibleEnquiries.length === 0 ? <p className="lede">No enquiries match the current filters.</p> : <div className="enquiry-table"><div className="enquiry-table-header"><span>Customer</span><span>Enquiry</span><span>Submitted</span><span>Status</span><span>Action</span></div>{visibleEnquiries.map(lead => <div className="enquiry-table-row" key={lead.id}><div><b>{lead.student_name}</b><small>{lead.student_email}</small></div><div><b>{lead.programme || "Programme not specified"}</b><small>{lead.academic_qualification || "Qualification not provided"}</small></div><small>{new Date(lead.created_at).toLocaleString()}</small><select value={lead.status} onChange={event => updateLead(lead, event.target.value)}><option>New</option><option>Submitted</option><option>Contacted</option><option>Interested</option><option>Qualified</option><option>Follow-up Required</option><option>Escalated</option><option>Converted</option><option>Not Interested</option></select><button className="outline-button" onClick={() => setSelectedEnquiry(lead)}>View details</button></div>)}</div>}<div className="pagination"><button className="outline-button" disabled={enquiryPage === 1} onClick={() => setEnquiryPage(page => page - 1)}>Previous</button><span>Page {enquiryPage} of {pageCount}</span><button className="outline-button" disabled={enquiryPage >= pageCount} onClick={() => setEnquiryPage(page => page + 1)}>Next</button></div></div>
    <div className="admin-grid"><div className="panel"><div className="panel-heading"><h3>Audit activity</h3><span>{logs.length} recent</span></div>{logs.slice(0, 8).map(log => <div className="audit-row" key={log.id}><b>{log.action}</b><span>{log.resource}</span><small>{new Date(log.created_at).toLocaleString()}</small></div>)}</div><div className="panel"><div className="panel-heading"><h3>Admin tools</h3><span>Workspace</span></div><p className="lede">Use Review enquiries to inspect user submissions. New enquiries can only be created from the student workspace.</p></div></div>
    <div className="panel model-panel"><div className="panel-heading"><h3>Ollama model configuration</h3><span>{models.length} local models</span></div><form className="model-form" onSubmit={saveModel}><label>Active model<select value={modelConfig.model_name} onChange={event => setModelConfig({ ...modelConfig, model_name: event.target.value })}>{models.map(model => <option key={model.name}>{model.name}</option>)}</select></label><label>Temperature<input type="number" min="0" max="2" step="0.1" value={modelConfig.temperature} onChange={event => setModelConfig({ ...modelConfig, temperature: Number(event.target.value) })} /></label><label>Top-p<input type="number" min="0" max="1" step="0.05" value={modelConfig.top_p} onChange={event => setModelConfig({ ...modelConfig, top_p: Number(event.target.value) })} /></label><label>Context length<input type="number" min="256" value={modelConfig.context_length} onChange={event => setModelConfig({ ...modelConfig, context_length: Number(event.target.value) })} /></label><button className="button">Save model settings</button></form></div>
    <div className="admin-grid"><div className="panel"><div className="panel-heading"><h3>Knowledge documents</h3><span>{documents.length} uploaded</span></div>{documents.map(document => <div className="audit-row" key={document.id}><b>{document.filename}</b><span>v{document.version} · {document.category}</span>{document.status === "ocr-required" && <button className="outline-button" onClick={() => runDocumentOcr(document)}>Run OCR</button>}<small>{document.status}</small></div>)}</div><div className="panel"><div className="panel-heading"><h3>Counsellor escalations</h3><span>{escalations.length} requests</span></div>{escalations.length === 0 ? <p className="lede">No escalations.</p> : escalations.map(item => <div className="audit-row" key={item.id}><b>{item.reason}</b><select value={item.status} onChange={event => updateEscalation(item, event.target.value)}><option>Pending</option><option>In Progress</option><option>Resolved</option><option>Cancelled</option></select><small>{new Date(item.created_at).toLocaleString()}</small></div>)}</div></div>
    <div className="admin-grid"><div className="panel"><div className="panel-heading"><h3>User management</h3><span>{users.length} accounts</span></div>{users.slice(0, 20).map(item => <div className="audit-row" key={item.id}><b>{item.name}</b><span>{item.email} · {item.enquiries} enquiries · {item.conversations} conversations</span><small>{item.interested_course || "No course selected"} · {item.login_status ? "Active" : "Inactive"}</small></div>)}</div><div className="panel"><div className="panel-heading"><h3>Course interests</h3><span>{courseInterests.length} tracked</span></div>{courseInterests.length === 0 ? <p className="lede">No course interests recorded.</p> : courseInterests.slice(0, 20).map(item => <div className="audit-row" key={item.id}><b>{item.programme}</b><span>{item.student_name} · {item.school || "School not specified"}</span><small>{item.status}</small></div>)}</div></div>
    <div className="admin-grid"><div className="panel"><div className="panel-heading"><h3>Student activity</h3><span>{activities.length} events</span></div>{activities.slice(0, 12).map(item => <div className="audit-row" key={item.id}><b>{item.activity_type.replaceAll("_", " ")}</b><span>{item.description}</span><small>{new Date(item.created_at).toLocaleString()}</small></div>)}</div><div className="panel"><div className="panel-heading"><h3>Follow-up queue</h3><span>{followUps.length} scheduled</span></div>{followUps.length === 0 ? <p className="lede">No follow-ups scheduled.</p> : followUps.map(item => <div className="audit-row" key={item.id}><b>Lead #{item.lead_id}</b><span>{new Date(item.due_at).toLocaleString()}</span><select value={item.status} onChange={event => updateFollowUp(item, event.target.value)}><option>Pending</option><option>In Progress</option><option>Completed</option><option>Cancelled</option></select></div>)}</div></div>
    {selectedEnquiry && <div className="modal-backdrop" onClick={() => setSelectedEnquiry(null)}><div className="modal enquiry-modal" onClick={event => event.stopPropagation()}><button type="button" className="close" onClick={() => setSelectedEnquiry(null)}>×</button><span className="eyebrow">ENQUIRY #{selectedEnquiry.id}</span><h2>{selectedEnquiry.student_name}</h2><div className="detail-grid"><b>Customer email</b><span>{selectedEnquiry.student_email}</span><b>Phone</b><span>{selectedEnquiry.student_phone || "Not provided"}</span><b>Programme</b><span>{selectedEnquiry.programme || "Not specified"}</span><b>Academic qualification</b><span>{selectedEnquiry.academic_qualification || "Not provided"}</span><b>Admission year</b><span>{selectedEnquiry.admission_year || "Not provided"}</span><b>Preferred department</b><span>{selectedEnquiry.preferred_department || "Not provided"}</span><b>Interests</b><span>{selectedEnquiry.interests || "Not provided"}</span><b>Submitted</b><span>{new Date(selectedEnquiry.created_at).toLocaleString()}</span></div><label className="detail-notes">Requirements / description<textarea value={selectedEnquiry.notes || ""} readOnly rows="4" /></label><label className="detail-status">Status<select value={selectedEnquiry.status} onChange={event => { updateLead(selectedEnquiry, event.target.value); setSelectedEnquiry({ ...selectedEnquiry, status: event.target.value }); }}><option>New</option><option>Submitted</option><option>Contacted</option><option>Interested</option><option>Qualified</option><option>Follow-up Required</option><option>Escalated</option><option>Converted</option><option>Not Interested</option></select></label></div></div>}
  </section>;
}
createRoot(document.getElementById("root")).render(<App />);
