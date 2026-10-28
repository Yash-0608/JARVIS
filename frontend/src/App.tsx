import { useCallback, useEffect, useRef, useState } from 'react';
import { Activity, ArrowUp, AudioLines, Check, ChevronDown, CircleHelp, Command, Cpu, Headphones, Link2, LoaderCircle, MessageSquare, Mic, MicOff, Monitor, MoreHorizontal, Phone, Plus, Radio, Send, Settings2, ShieldCheck, Smartphone, Sparkles, Volume2, VolumeX, Wifi, X } from 'lucide-react';

import type { ReactNode } from 'react';

type ChatMessage = { role: 'user' | 'assistant'; content: string };
type Device = { id: string; device_name: string; device_platform: string; paired_at: string };
type PairRequest = { request_id: string; device_name: string; device_platform: string; created_at: string; state: string };
const API = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const API_KEY = import.meta.env.VITE_JARVIS_API_KEY || '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...init, headers: { ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), 'X-JARVIS-API-Key': API_KEY } });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
  return data as T;
}

export default function App() {
  const [page, setPage] = useState<'assistant' | 'devices' | 'connections'>('assistant');
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: 'assistant', content: 'Hi, I’m JARVIS. What would you like to work on?' }]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [ollama, setOllama] = useState<{connected: boolean; base_url?: string; error?: string}>({ connected: false });
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState('');
  const [pairCode, setPairCode] = useState('');
  const [pairExpiry, setPairExpiry] = useState(0);
  const [pairRequests, setPairRequests] = useState<PairRequest[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [integrationStates, setIntegrationStates] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [recording, setRecording] = useState(false);
  const [voiceOutput, setVoiceOutput] = useState(true);
  const [voiceMeta, setVoiceMeta] = useState('');
  const [transcribing, setTranscribing] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  const refreshStatus = useCallback(async () => {
    try {
      const status = await request<{connected:boolean;base_url?:string;error?:string}>('/api/ollama/status');
      setOllama(status);
      if (status.connected) {
        const result = await request<{models:{name:string}[]}>('/api/ollama/models');
        const names = result.models.map(item => item.name);
        setModels(names);
        setModel(current => current && names.includes(current) ? current : (names[0] || ''));
      } else setModels([]);
      try { const statusList = await request<{items:{id:string;state:string}[]}>('/api/integrations'); setIntegrationStates(Object.fromEntries(statusList.items.map(item => [item.id, item.state]))); } catch { /* Keep last-known connector states. */ }
    } catch (e) { setOllama({ connected: false, error: e instanceof Error ? e.message : 'Backend unavailable' }); }
  }, []);

  const refreshPairing = useCallback(async () => {
    try {
      const [r, d] = await Promise.all([
        request<{requests:PairRequest[]}>('/api/pairing/requests'),
        request<{devices:Device[]}>('/api/pairing/devices'),
      ]);
      setPairRequests(r.requests); setDevices(d.devices);
    } catch { /* Backend may not have started yet. */ }
  }, []);

  useEffect(() => {
    void refreshStatus(); void refreshPairing();
    const statusTimer = window.setInterval(() => void refreshStatus(), 12000);
    const pairTimer = window.setInterval(() => { void refreshPairing(); setPairExpiry(value => Math.max(0, value - 2)); }, 2000);
    return () => { window.clearInterval(statusTimer); window.clearInterval(pairTimer); };
  }, [refreshStatus, refreshPairing]);

  async function sendMessage(content = draft) {
    const text = content.trim(); if (!text || busy) return;
    setError(''); setDraft(''); setMessages(prev => [...prev, { role: 'user', content: text }]); setBusy(true);
    try {
      const result = await request<{response:string}>('/api/ollama/chat', { method: 'POST', body: JSON.stringify({ message: text, model: model || undefined }) });
      const answer = result.response || 'The model returned an empty response.';
      setMessages(prev => [...prev, { role: 'assistant', content: answer }]);
      if (voiceOutput && 'speechSynthesis' in window) { window.speechSynthesis.cancel(); const utterance = new SpeechSynthesisUtterance(answer); utterance.lang = /[ऀ-ॿ]/.test(answer) ? 'hi-IN' : 'en-IN'; window.speechSynthesis.speak(utterance); }
    } catch (e) { const message = e instanceof Error ? e.message : 'Unable to reach JARVIS backend'; setError(message); setMessages(prev => [...prev, { role: 'assistant', content: `I couldn’t reach the local model. ${message}` }]); }
    finally { setBusy(false); }
  }

  async function createCode() {
    setError('');
    try { const data = await request<{code:string;expires_in:number}>('/api/pairing/code', { method:'POST' }); setPairCode(data.code); setPairExpiry(data.expires_in); }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not create pairing code'); }
  }

  async function decidePairing(item: PairRequest, accept: boolean) {
    try { await request('/api/pairing/decision', { method:'POST', body: JSON.stringify({request_id:item.request_id, accept}) }); await refreshPairing(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Pairing decision failed'); }
  }

  async function toggleRecording() {
    setError('');
    if (recording && recorder.current) { recorder.current.stop(); setRecording(false); return; }
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) { setError('Microphone recording is not supported in this browser.'); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const preferred = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : '';
      const media = new MediaRecorder(stream, preferred ? { mimeType: preferred } : undefined);
      chunks.current = []; recorder.current = media;
      media.ondataavailable = event => { if (event.data.size) chunks.current.push(event.data); };
      media.onerror = () => { setError('Recording failed. Check microphone permission.'); setRecording(false); stream.getTracks().forEach(track => track.stop()); };
      media.onstop = async () => {
        stream.getTracks().forEach(track => track.stop()); setTranscribing(true);
        try {
          const form = new FormData(); form.append('audio', new Blob(chunks.current, { type: media.mimeType || 'audio/webm' }), 'voice.webm');
          const result = await request<{text:string;language:string;language_probability:number}>('/api/speech/transcribe', { method:'POST', body:form });
          setVoiceMeta(`Detected language: ${result.language.toUpperCase()} · ${Math.round(result.language_probability * 100)}% confidence`);
          if (result.text.trim()) await sendMessage(result.text.trim());
          else setError('No speech was detected. Try again in a quieter place.');
        } catch (e) { setError(e instanceof Error ? e.message : 'Transcription failed'); }
        finally { setTranscribing(false); }
      };
      media.start(); setRecording(true);
    } catch (e) { setError(e instanceof Error ? e.message : 'Microphone permission denied'); }
  }

  const nav = [
    { id: 'assistant' as const, label: 'Assistant', icon: MessageSquare },
    { id: 'devices' as const, label: 'Phone & devices', icon: Smartphone },
    { id: 'connections' as const, label: 'Connections', icon: Link2 },
  ];

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><AudioLines size={21}/></div><div><strong>JARVIS</strong><span>PERSONAL AI</span></div></div>
      <button className="workspace-button"><div className="workspace-glyph">Y</div><div className="workspace-copy"><strong>My workspace</strong><span>Local environment</span></div><ChevronDown size={15}/></button>
      <div className="nav-label">WORKSPACE</div>
      <nav>{nav.map(item => <button key={item.id} onClick={() => setPage(item.id)} className={`nav-item ${page === item.id ? 'active' : ''}`}><item.icon size={18}/><span>{item.label}</span>{item.id === 'devices' && devices.length > 0 && <em>{devices.length}</em>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="local-card"><div className="local-row"><span className={`status-dot ${ollama.connected ? 'online' : ''}`}/><strong>{ollama.connected ? 'Local AI connected' : 'Waiting for local AI'}</strong></div><p>{ollama.connected ? (model || 'Ollama is ready') : 'Start the backend and Ollama to begin.'}</p><div className="local-foot"><ShieldCheck size={14}/> Your model runs locally</div></div><button className="nav-item muted" onClick={() => setError('Settings are currently configured through backend/.env and frontend/.env.')}><Settings2 size={18}/> Settings</button><div className="profile"><div className="avatar">Y</div><div className="profile-copy"><strong>Yash</strong><span>Personal assistant</span></div><MoreHorizontal size={18}/></div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><span className="crumb-slash">/</span><strong>{nav.find(item => item.id === page)?.label}</strong></div><div className="top-actions"><span className="privacy-label"><span className="status-dot online"/> Local-first mode</span><button className="icon-button" title="Help" onClick={() => setError('JARVIS is a local-first assistant. Configure backend/.env, start Ollama, and keep the local API private.')}><CircleHelp size={18}/></button></div></header>
      {page === 'assistant' && <section className="assistant-page">
        <div className="welcome-heading"><div className="eyebrow"><Sparkles size={14}/> YOUR PERSONAL AI</div><h1>A little help, <span>whenever you need it.</span></h1><p>Talk naturally. Think together. Get things done.</p></div>
        <div className="status-grid"><div className="status-card"><div className="status-icon lavender"><Cpu size={18}/></div><div className="status-content"><span>AI model</span><strong>{ollama.connected ? (model || 'Connected') : 'Not connected'}</strong></div><span className={`mini-status ${ollama.connected ? 'good' : ''}`}>{ollama.connected ? 'Ready' : 'Offline'}</span></div><div className="status-card"><div className="status-icon blue"><Mic size={18}/></div><div className="status-content"><span>Voice input</span><strong>Speech to text</strong></div><span className="mini-status">On demand</span></div><div className="status-card"><div className="status-icon mint"><Smartphone size={18}/></div><div className="status-content"><span>Phone link</span><strong>{devices.length ? `${devices.length} device linked` : 'No device linked'}</strong></div><button className="subtle-link" onClick={() => setPage('devices')}>Manage</button></div></div>
        <div className="chat-card"><div className="chat-header"><div><h2>Conversation</h2><p>Private session · Runs on your setup</p></div><button className={`voice-toggle ${voiceOutput ? 'on' : ''}`} onClick={() => { setVoiceOutput(value => !value); if (voiceOutput && 'speechSynthesis' in window) window.speechSynthesis.cancel(); }} title={voiceOutput ? 'Mute spoken replies' : 'Enable spoken replies'} aria-label={voiceOutput ? 'Mute spoken replies' : 'Enable spoken replies'}>{voiceOutput ? <Volume2 size={16}/> : <VolumeX size={16}/>}</button><div className="model-select-wrap"><span className={`status-dot ${ollama.connected ? 'online' : ''}`}/><select value={model} onChange={e => setModel(e.target.value)} disabled={!models.length} aria-label="Ollama model">{models.length ? models.map(name => <option key={name} value={name}>{name}</option>) : <option value="">Model unavailable</option>}</select><ChevronDown size={13}/></div></div>
          <div className="message-list">{messages.map((message, index) => <div key={`${index}-${message.role}`} className={`message-row ${message.role}`}><div className={`message-avatar ${message.role}`}>{message.role === 'assistant' ? <AudioLines size={16}/> : 'Y'}</div><div className="message-body"><span className="message-author">{message.role === 'assistant' ? 'JARVIS' : 'YOU'} <time>{index === 0 ? 'Just now' : ''}</time></span><div className="message-text">{message.content}</div></div></div>)}{busy && <div className="message-row assistant"><div className="message-avatar assistant"><AudioLines size={16}/></div><div className="message-body"><span className="message-author">JARVIS</span><div className="typing"><i/><i/><i/></div></div></div>}</div>
          <form className="composer" onSubmit={e => { e.preventDefault(); void sendMessage(); }}><textarea value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void sendMessage(); } }} placeholder="Ask JARVIS anything…" rows={2}/><div className="composer-bottom"><div className="composer-hints"><span><Command size={12}/> Enter to send</span><span>·</span><span>Shift + Enter for new line</span>{voiceMeta && <span className="voice-meta">{voiceMeta}</span>}</div><div className="composer-buttons"><button type="button" className={`mic-button ${recording ? 'recording' : ''}`} onClick={() => void toggleRecording()} disabled={busy || transcribing} title={recording ? 'Stop recording' : 'Record voice'}>{transcribing ? <LoaderCircle className="spin" size={17}/> : recording ? <MicOff size={17}/> : <Mic size={17}/>}</button><button type="submit" className="send-button" disabled={!draft.trim() || busy}><span>Send</span><ArrowUp size={16}/></button></div></div></form>
          <div className="privacy-note"><ShieldCheck size={14}/> Your conversation is sent to the configured local Ollama endpoint. Don’t enter passwords or access tokens.</div>
        </div>
        <div className="suggestion-row"><span>TRY ASKING</span><button onClick={() => void sendMessage('Help me plan my day in a simple, realistic way.')}>Plan my day <ArrowUp size={13}/></button><button onClick={() => void sendMessage('Explain how to connect my Android phone to this JARVIS desktop app securely.')}>Connect my phone <ArrowUp size={13}/></button><button onClick={() => void sendMessage('Give me a quick check of my local AI setup and what I should configure next.')}>Check my setup <ArrowUp size={13}/></button></div>
      </section>}

      {page === 'devices' && <section className="content-page"><div className="page-heading"><div className="eyebrow"><Smartphone size={14}/> DEVICE ECOSYSTEM</div><h1>Your phone, <span>connected thoughtfully.</span></h1><p>Pair Android with a simple request-and-accept flow, like PhoneCast.</p></div><div className="pair-layout"><div className="panel pair-panel"><div className="panel-icon"><Wifi size={20}/></div><h2>Pair a new device</h2><p>Generate a short-lived code on Windows, then enter it in the JARVIS Android companion on the same trusted Wi-Fi network.</p>{pairCode ? <div className="pair-code"><span>PAIRING CODE</span><strong>{pairCode}</strong><small>{pairExpiry > 0 ? `Expires in about ${pairExpiry}s` : 'Code expired — generate a new one'}</small></div> : <div className="pair-placeholder"><Smartphone size={28}/><span>Your Android device will request access here.</span></div>}<button className="primary-button full" onClick={() => void createCode()}><Plus size={17}/>{pairCode && pairExpiry > 0 ? 'Generate another code' : 'Generate pairing code'}</button><div className="pair-safety"><ShieldCheck size={15}/><span>Pairing codes expire quickly and can be used once. This development flow should only be used on a trusted local network.</span></div></div><div className="panel request-panel"><div className="panel-top"><div><h2>Connection requests</h2><p>Review each device before granting access.</p></div><span className="count-badge">{pairRequests.length}</span></div>{pairRequests.length ? pairRequests.map(item => <div className="request-item" key={item.request_id}><div className="device-icon"><Smartphone size={19}/></div><div className="request-info"><strong>{item.device_name}</strong><span>{item.device_platform} · Requests pairing</span></div><div className="request-actions"><button className="accept-button" onClick={() => void decidePairing(item, true)} title="Accept request"><Check size={16}/></button><button className="reject-button" onClick={() => void decidePairing(item, false)} title="Reject request"><X size={16}/></button></div></div>) : <div className="empty-state"><div className="empty-visual"><Radio size={24}/></div><strong>Nothing waiting right now</strong><span>New phone requests will appear here.</span></div>}<div className="panel-separator"/><div className="linked-header"><h3>Linked devices</h3><span>{devices.length} linked</span></div>{devices.map(device => <div className="request-item" key={device.id}><div className="device-icon connected"><Smartphone size={19}/></div><div className="request-info"><strong>{device.device_name}</strong><span>{device.device_platform} · Paired</span></div><span className="connected-label"><span className="status-dot online"/> Linked</span></div>)}</div></div><div className="notice-strip"><CircleHelp size={17}/><p>Pairing is a foundation only. Notifications, call state, file transfer and remote controls each need a separate permissioned implementation in the Android app.</p></div></section>}

      {page === 'connections' && <section className="content-page"><div className="page-heading"><div className="eyebrow"><Link2 size={14}/> INTEGRATIONS</div><h1>Everything in <span>its right place.</span></h1><p>Manage which tools JARVIS can reach, and see what is still waiting for setup.</p></div><div className="integration-list"><Integration icon={<Cpu size={20}/>} title="Ollama / Qwen" description={ollama.connected ? `Connected at ${ollama.base_url}` : `Not reachable. ${ollama.error || 'Start Ollama and the backend.'}`} state={ollama.connected ? 'Connected' : 'Offline'} kind={ollama.connected ? 'good' : 'warn'}/><Integration icon={<AudioLines size={20}/>} title="Speech recognition" description="Local transcription and detected-language metadata. First use may download model weights." state="On demand" kind="neutral"/><Integration icon={<Smartphone size={20}/>} title="Android companion" description="Pairing request protocol is available; build and install the companion to continue." state={devices.length ? 'Paired' : 'Setup required'} kind={devices.length ? 'good' : 'neutral'} action={() => setPage('devices')}/><Integration icon={<MessageSquare size={20}/>} title="WhatsApp" description="Requires a supported official API path, account configuration, and granted permissions. Personal chat access is not assumed." state={integrationStates.whatsapp === "credentials_ready" ? "Credentials ready" : "Needs setup"} kind={integrationStates.whatsapp === "credentials_ready" ? "good" : "neutral"}/><Integration icon={<Activity size={20}/>} title="Instagram" description="Requires supported Meta APIs and permissions. Some personal-account DM workflows may not be available." state={integrationStates.instagram === "credentials_ready" ? "Credentials ready" : "Needs setup"} kind={integrationStates.instagram === "credentials_ready" ? "good" : "neutral"}/><Integration icon={<Phone size={20}/>} title="Calls & telephony" description="Direct call control is not implemented yet; Android OS role, permissions, and device testing are required." state="Not implemented" kind="warn"/><Integration icon={<Monitor size={20}/>} title="Windows automation" description="Intent detection is preview-only until an allow-listed executor is added and locally validated." state="Scaffold" kind="neutral"/></div><SocialSendForms status={integrationStates}/><div className="notice-strip"><ShieldCheck size={17}/><p>JARVIS won’t bypass platform security, guess credentials, or claim an action succeeded without a verified result. Sensitive messaging and calling actions should require confirmation.</p></div></section>}

      <footer className="app-footer"><span>JARVIS <b>v0.1.0</b></span><span><span className={`status-dot ${ollama.connected ? 'online' : ''}`}/>{ollama.connected ? 'Local model online' : 'Waiting for backend'}</span><span>Built for your workspace</span></footer>
    </main>
    {error && <div role="alert" className="toast"><div className="toast-icon"><CircleHelp size={17}/></div><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss"><X size={16}/></button></div>}
  </div>;
}


function SocialSendForms({status}: {status: Record<string, string>}) {
  const [waTo, setWaTo] = useState('');
  const [waText, setWaText] = useState('');
  const [waConfirm, setWaConfirm] = useState(false);
  const [igTo, setIgTo] = useState('');
  const [igText, setIgText] = useState('');
  const [igConfirm, setIgConfirm] = useState(false);
  const [result, setResult] = useState('');
  const [busy, setBusy] = useState(false);
  async function submit(path: string, body: object) {
    setBusy(true); setResult('');
    try {
      const response = await request<{submitted?: boolean; message_id?: string}>(path, {method:'POST', body:JSON.stringify(body)});
      setResult("Provider accepted the request" + (response.message_id ? " · ID " + response.message_id : "") + ". Check the provider account for delivery status.");
    } catch (e) { setResult(e instanceof Error ? e.message : 'Could not send message.'); }
    finally { setBusy(false); }
  }
  return <div className="social-send-grid">
    <form className="panel social-send-panel" onSubmit={e => { e.preventDefault(); void submit('/api/social/whatsapp/send', {to:waTo,text:waText,confirmed:true}); }}>
      <div className="social-form-head"><div className="integration-icon"><MessageSquare size={19}/></div><div><h2>WhatsApp message</h2><p>{status.whatsapp === 'credentials_ready' ? 'Cloud API credentials detected' : 'Configure the official Cloud API in backend/.env'}</p></div></div>
      <label>Recipient phone (international format)</label><input value={waTo} onChange={e => { setWaTo(e.target.value); setWaConfirm(false); setResult(""); }} placeholder="+91 98xxxxxxxx" required maxLength={30} disabled={busy}/>
      <label>Message</label><textarea value={waText} onChange={e => { setWaText(e.target.value); setWaConfirm(false); setResult(""); }} placeholder="Write the message you want to send…" rows={3} maxLength={4096} required disabled={busy}/>
      <label className="confirm-check"><input type="checkbox" checked={waConfirm} onChange={e => setWaConfirm(e.target.checked)} disabled={busy}/> I reviewed the recipient and exact message.</label>
      <button className="primary-button full" disabled={busy || !waConfirm || status.whatsapp !== 'credentials_ready'}><Send size={15}/> Send approved message</button>
    </form>
    <form className="panel social-send-panel" onSubmit={e => { e.preventDefault(); void submit('/api/social/instagram/send', {recipient_id:igTo,text:igText,confirmed:true}); }}>
      <div className="social-form-head"><div className="integration-icon"><Activity size={19}/></div><div><h2>Instagram message</h2><p>{status.instagram === 'credentials_ready' ? 'Graph API credentials detected' : 'Configure the professional-account API in backend/.env'}</p></div></div>
      <label>Instagram-scoped recipient ID</label><input value={igTo} onChange={e => { setIgTo(e.target.value); setIgConfirm(false); setResult(""); }} placeholder="Recipient ID from an allowed conversation" required maxLength={30} disabled={busy}/>
      <label>Message</label><textarea value={igText} onChange={e => { setIgText(e.target.value); setIgConfirm(false); setResult(""); }} placeholder="Write the message you want to send…" rows={3} maxLength={1000} required disabled={busy}/>
      <label className="confirm-check"><input type="checkbox" checked={igConfirm} onChange={e => setIgConfirm(e.target.checked)} disabled={busy}/> I reviewed the recipient and exact message.</label>
      <button className="primary-button full" disabled={busy || !igConfirm || status.instagram !== 'credentials_ready'}><Send size={15}/> Send approved message</button>
    </form>
    {result && <div className="social-result" role="status">{result}</div>}
  </div>;
}

function Integration({icon, title, description, state, kind, action}: {icon: ReactNode; title: string; description: string; state: string; kind: string; action?: () => void}) {
  return <div className="integration-item"><div className="integration-icon">{icon}</div><div className="integration-copy"><strong>{title}</strong><p>{description}</p></div><span className={`integration-state ${kind}`}>{state}</span>{action && <button className="integration-action" onClick={action}>Configure <ArrowUp size={13}/></button>}</div>;
}
