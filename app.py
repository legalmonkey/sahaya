"""A loopback-only offline field shell for Sahaya (Track C).
Adopts the Forest Green Figma design language, zero-login household triage,
deterministic priority ranking, and multi-turn voice assistant flow.
"""
from __future__ import annotations

import json
import os
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.database import initialise
from src.inference import InferenceUnavailable, SahayaPipeline
from src.prioritization import PrioritizationEngine
from src.retrieval import LocalTfidfRetriever
from src.voice import AsrUnavailable, LocalSpeechTranscriber

ROOT = Path(__file__).parent
DB_PATH = ROOT / "data" / "sahaya.db"
MIGRATION_PATH = ROOT / "db" / "migrations" / "001_shared_schema.sql"
CORPUS_PATH = ROOT / "data" / "corpus.json"

# Initialize local database and services
initialise(DB_PATH, MIGRATION_PATH)
PRIORITIZER = PrioritizationEngine(DB_PATH)
PIPELINE = SahayaPipeline(LocalTfidfRetriever(CORPUS_PATH))
TRANSCRIBER = LocalSpeechTranscriber()

# Run an initial priority recalculation on startup
with sqlite3.connect(DB_PATH) as conn:
    PRIORITIZER.refresh_priority_queue(conn)

PAGE_HTML = """<!doctype html>
<html lang="hi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <title>सहया • Sahaya — ASHA Field Assistant</title>
  <style>
    :root {
      --primary: #126b50;
      --primary-dark: #0e4d3a;
      --primary-light: #e8f5f0;
      --surface: #ffffff;
      --surface-subtle: #f0f7f4;
      --bg: #f8faf9;
      --text-main: #17352b;
      --text-muted: #57665f;
      --border: #dbe6e0;
      --danger: #d9383a;
      --danger-bg: #fde8e8;
      --warning: #d97706;
      --warning-bg: #fef3c7;
      --success: #16a34a;
      --success-bg: #dcfce7;
      --radius: 14px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      line-height: 1.45;
      padding-bottom: 5rem;
      -webkit-font-smoothing: antialiased;
    }
    header {
      background: var(--primary);
      color: white;
      padding: 0.9rem 1.1rem;
      position: sticky;
      top: 0;
      z-index: 50;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 2px 8px rgba(18, 107, 80, 0.2);
    }
    .brand { display: flex; align-items: center; gap: 0.6rem; }
    .brand-icon {
      width: 32px; height: 32px; background: rgba(255,255,255,0.2);
      border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
    }
    .brand-title { font-size: 1.15rem; font-weight: 700; letter-spacing: -0.2px; }
    .brand-subtitle { font-size: 0.72rem; opacity: 0.88; }
    .header-actions { display: flex; align-items: center; gap: 0.5rem; }
    .badge-pill {
      background: rgba(255,255,255,0.18);
      padding: 0.25rem 0.65rem;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
    }

    .container { max-width: 640px; margin: 0 auto; padding: 1rem; }
    .view { display: none; }
    .view.active { display: block; animation: fadeIn 0.2s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

    /* Urgency stats strip */
    .triage-strip {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 0.6rem;
      margin-bottom: 1rem;
    }
    .triage-stat {
      background: var(--surface);
      border-radius: var(--radius);
      padding: 0.65rem 0.5rem;
      text-align: center;
      border: 1px solid var(--border);
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .triage-stat .num { font-size: 1.3rem; font-weight: 800; }
    .triage-stat .label { font-size: 0.72rem; font-weight: 600; color: var(--text-muted); }
    .triage-stat.high .num { color: var(--danger); }
    .triage-stat.medium .num { color: var(--warning); }
    .triage-stat.low .num { color: var(--success); }

    /* Search & Filter */
    .search-box {
      margin-bottom: 1rem;
      position: relative;
    }
    .search-box input {
      width: 100%;
      padding: 0.75rem 1rem 0.75rem 2.4rem;
      border-radius: var(--radius);
      border: 1px solid var(--border);
      font-size: 0.95rem;
      background: var(--surface);
      outline: none;
    }
    .search-box .icon {
      position: absolute;
      left: 0.8rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
    }

    /* Household Cards */
    .card-list { display: flex; flex-direction: column; gap: 0.75rem; }
    .household-card {
      background: var(--surface);
      border-radius: var(--radius);
      border: 1px solid var(--border);
      border-left-width: 6px;
      padding: 0.9rem 1rem;
      box-shadow: 0 2px 5px rgba(0,0,0,0.03);
      cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    .household-card:active { transform: scale(0.99); }
    .household-card.urgency-high { border-left-color: var(--danger); }
    .household-card.urgency-medium { border-left-color: var(--warning); }
    .household-card.urgency-low { border-left-color: var(--success); }

    .card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem; }
    .household-title { font-size: 1.05rem; font-weight: 700; color: var(--text-main); }
    .household-village { font-size: 0.78rem; color: var(--text-muted); }
    .tier-badge {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }
    .tier-badge.high { background: var(--danger-bg); color: var(--danger); }
    .tier-badge.medium { background: var(--warning-bg); color: var(--warning); }
    .tier-badge.low { background: var(--success-bg); color: var(--success); }

    .reasons-box { margin: 0.5rem 0; display: flex; flex-direction: column; gap: 0.3rem; }
    .reason-chip {
      font-size: 0.8rem;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 0.4rem;
      background: var(--surface-subtle);
      padding: 0.25rem 0.55rem;
      border-radius: 6px;
    }
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 0.5rem;
      padding-top: 0.5rem;
      border-top: 1px dashed var(--border);
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    /* FAB */
    .fab {
      position: fixed;
      right: 1.25rem;
      bottom: 1.5rem;
      width: 58px;
      height: 58px;
      background: var(--primary);
      color: white;
      border-radius: 50%;
      border: none;
      box-shadow: 0 4px 14px rgba(18, 107, 80, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.6rem;
      cursor: pointer;
      z-index: 90;
      transition: transform 0.15s ease;
    }
    .fab:active { transform: scale(0.92); }

    /* Household Detail View */
    .nav-back {
      background: transparent;
      border: none;
      color: var(--primary);
      font-size: 0.95rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      cursor: pointer;
      margin-bottom: 0.8rem;
    }
    .detail-hero {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.1rem;
      margin-bottom: 1rem;
    }
    .context-chip {
      background: var(--primary-light);
      color: var(--primary-dark);
      font-weight: 700;
      font-size: 0.8rem;
      padding: 0.35rem 0.7rem;
      border-radius: 8px;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      margin-bottom: 0.6rem;
    }
    .module-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1rem;
      margin-bottom: 0.8rem;
    }
    .module-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 0.7rem;
    }
    .module-title {
      font-size: 0.98rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 0.45rem;
    }
    .item-row {
      padding: 0.45rem 0;
      border-bottom: 1px solid #edf2ef;
      font-size: 0.86rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .item-row:last-child { border-bottom: none; }

    /* Voice / Conversation Overlay Screen */
    .voice-sheet {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: var(--bg);
      z-index: 100;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    .voice-topbar {
      background: var(--surface);
      padding: 0.9rem 1rem;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .chat-stream {
      flex: 1;
      overflow-y: auto;
      padding: 1rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    .chat-bubble {
      max-width: 86%;
      border-radius: 14px;
      padding: 0.85rem 1rem;
      font-size: 0.92rem;
      line-height: 1.45;
    }
    .chat-bubble.user {
      align-self: flex-end;
      background: var(--primary);
      color: white;
      border-bottom-right-radius: 4px;
    }
    .chat-bubble.assistant {
      align-self: flex-start;
      background: var(--surface);
      color: var(--text-main);
      border: 1px solid var(--border);
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    }
    .citation-tag {
      margin-top: 0.6rem;
      padding: 0.4rem 0.6rem;
      background: var(--surface-subtle);
      border-left: 3px solid var(--primary);
      border-radius: 4px;
      font-size: 0.74rem;
      color: var(--text-muted);
    }
    .confidence-badge {
      display: inline-block;
      margin-top: 0.4rem;
      font-size: 0.72rem;
      font-weight: 700;
      color: var(--primary);
    }

    /* ⭐ Multi-turn Listening Cue */
    .followup-listening-box {
      align-self: center;
      display: flex;
      align-items: center;
      gap: 0.6rem;
      background: var(--primary-light);
      color: var(--primary-dark);
      padding: 0.6rem 1.1rem;
      border-radius: 24px;
      font-size: 0.85rem;
      font-weight: 600;
      animation: pulse 1.8s infinite;
      margin: 0.5rem 0;
    }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(18, 107, 80, 0.35); }
      70% { box-shadow: 0 0 0 10px rgba(18, 107, 80, 0); }
      100% { box-shadow: 0 0 0 0 rgba(18, 107, 80, 0); }
    }

    .voice-controls {
      background: var(--surface);
      border-top: 1px solid var(--border);
      padding: 0.8rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }
    .input-bar {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .input-bar input {
      flex: 1;
      padding: 0.75rem 1rem;
      border: 1px solid var(--border);
      border-radius: 24px;
      font-size: 0.92rem;
      outline: none;
    }
    .btn-mic {
      width: 46px;
      height: 46px;
      border-radius: 50%;
      background: var(--primary);
      color: white;
      border: none;
      font-size: 1.3rem;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
    }
    .btn-mic.recording {
      background: var(--danger);
      animation: pulse 1.2s infinite;
    }
    .btn-send {
      padding: 0.65rem 1rem;
      background: var(--primary);
      color: white;
      border: none;
      border-radius: 20px;
      font-weight: 600;
      cursor: pointer;
    }
    .quick-prompts {
      display: flex;
      gap: 0.4rem;
      overflow-x: auto;
      padding: 0.3rem 0;
    }
    .quick-chip {
      white-space: nowrap;
      background: var(--surface-subtle);
      border: 1px solid var(--border);
      padding: 0.3rem 0.65rem;
      border-radius: 16px;
      font-size: 0.76rem;
      color: var(--text-main);
      cursor: pointer;
    }

    .empty-placeholder {
      text-align: center;
      padding: 2.5rem 1rem;
      color: var(--text-muted);
    }
    .btn-action {
      background: var(--primary);
      color: white;
      border: none;
      padding: 0.7rem 1.2rem;
      border-radius: 10px;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      margin-top: 0.8rem;
    }
  </style>
</head>
<body>

  <!-- App Header -->
  <header>
    <div class="brand">
      <div class="brand-icon">🌿</div>
      <div>
        <div class="brand-title">सहया • Sahaya</div>
        <div class="brand-subtitle">ऑफलाइन एआई फील्ड सहायक • रामपुर</div>
      </div>
    </div>
    <div class="header-actions">
      <div class="badge-pill" id="lang-btn" onclick="toggleLang()">🌐 हिन्दी</div>
      <div class="badge-pill" onclick="refreshPriorities()" title="प्राथमिकता सूची ताज़ा करें">🔄 ताज़ा</div>
    </div>
  </header>

  <div class="container">

    <!-- VIEW 1: Household Prioritized Triage List (Zero-login launch) -->
    <section id="households-view" class="view active">
      <div class="triage-strip">
        <div class="triage-stat high">
          <div class="num" id="stat-high">0</div>
          <div class="label">अति आवश्यक</div>
        </div>
        <div class="triage-stat medium">
          <div class="num" id="stat-medium">0</div>
          <div class="label">मध्यम</div>
        </div>
        <div class="triage-stat low">
          <div class="num" id="stat-low">0</div>
          <div class="label">सामान्य</div>
        </div>
      </div>

      <div class="search-box">
        <span class="icon">🔍</span>
        <input type="text" id="search-input" placeholder="घर का नाम या कारण खोजें..." oninput="filterCards()">
      </div>

      <div id="households-list" class="card-list">
        <div class="empty-placeholder">
          डेटा लोड हो रहा है...
        </div>
      </div>
    </section>

    <!-- VIEW 2: Household Detail View -->
    <section id="detail-view" class="view">
      <button class="nav-back" onclick="showView('households-view')">← परिवार सूची पर वापस जाएं</button>
      <div id="detail-content"></div>
    </section>

  </div>

  <!-- Floating Mic Button -->
  <button class="fab" id="main-fab" onclick="openVoiceAssistant()" title="आवाज़ से सवाल पूछें">🎙️</button>

  <!-- VIEW 3: Voice & Multi-Turn Conversation Overlay -->
  <div id="voice-sheet" class="voice-sheet" style="display: none;">
    <div class="voice-topbar">
      <div>
        <div style="font-weight: 700; font-size: 1.05rem;" id="voice-title">सहया संवाद सहायक</div>
        <div style="font-size: 0.75rem; color: var(--text-muted);" id="voice-context-pill">📍 सामान्य प्रोटोकॉल मोड</div>
      </div>
      <div style="display: flex; gap: 0.5rem;">
        <button class="badge-pill" onclick="resetConversation()" title="नयी बातचीत शुरू करें" style="background: #edf3f0; color: var(--text-main);">नयी बातचीत</button>
        <button class="badge-pill" onclick="closeVoiceAssistant()" style="background: #edf3f0; color: var(--text-main);">✕ बंद करें</button>
      </div>
    </div>

    <!-- Live Conversation Stream -->
    <div id="chat-stream" class="chat-stream">
      <div class="chat-bubble assistant">
        नमस्ते आशा दीदी! मैं सहया हूँ। टीकाकरण, गर्भावस्था जोखिम या सरकारी योजनाओं से जुड़ा कोई भी सवाल बोलकर या लिखकर पूछें।
      </div>
    </div>

    <!-- Multi-turn Listening Cue (Ambient indicator) -->
    <div id="followup-listening-indicator" class="followup-listening-box" style="display: none;">
      <span>🎙️</span>
      <span>सुन रहा हूँ... अगला सवाल पूछें (संदर्भ सुरक्षित है)</span>
    </div>

    <!-- Voice / Input Controls -->
    <div class="voice-controls">
      <div class="quick-prompts" id="quick-prompts">
        <div class="quick-chip" onclick="askQuick('ओपीवी टीका कब दिया जाता है?')">ओपीवी टीका अनुसूची</div>
        <div class="quick-chip" onclick="askQuick('गर्भावस्था में उच्च रक्तचाप के क्या खतरे हैं?')">उच्च रक्तचाप खतरे</div>
        <div class="quick-chip" onclick="askQuick('पीएमएमवीवाई योजना में कितनी सहायता मिलती है?')">पीएमएमवीवाई योजना</div>
      </div>
      <div class="input-bar">
        <button class="btn-mic" id="voice-mic-btn" onclick="toggleVoiceInput()" title="बोलकर पूछें">🎙️</button>
        <input type="text" id="voice-text-input" placeholder="सवाल बोलें या लिखें..." onkeydown="if(event.key==='Enter') sendQuestion()">
        <button class="btn-send" onclick="sendQuestion()">भेजें</button>
      </div>
    </div>
  </div>

  <script>
    let allHouseholds = [];
    let currentHousehold = null;
    let conversationBuffer = []; // [{query, answer}]
    let activeLanguage = 'hi';
    let isListening = false;
    let recognition = null;

    // Initialize Web Speech Recognition if available (offline capable on modern browsers/phones)
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'hi-IN';

      recognition.onstart = () => {
        isListening = true;
        document.getElementById('voice-mic-btn').classList.add('recording');
        document.getElementById('voice-text-input').placeholder = 'सुन रहा हूँ... बोलिए';
      };

      recognition.onresult = (e) => {
        const text = e.results[0][0].transcript;
        document.getElementById('voice-text-input').value = text;
        sendQuestion();
      };

      recognition.onerror = () => { stopListening(); };
      recognition.onend = () => { stopListening(); };
    }

    function toggleVoiceInput() {
      if (!recognition) {
        alert('आपके ब्राउज़र में डायरेक्ट वॉयस एपीआई उपलब्ध नहीं है। कृपया नीचे लिखकर सवाल पूछें।');
        return;
      }
      if (isListening) {
        recognition.stop();
        stopListening();
      } else {
        recognition.lang = activeLanguage === 'ta' ? 'ta-IN' : (activeLanguage === 'en' ? 'en-IN' : 'hi-IN');
        recognition.start();
      }
    }

    function stopListening() {
      isListening = false;
      const btn = document.getElementById('voice-mic-btn');
      if (btn) btn.classList.remove('recording');
      const input = document.getElementById('voice-text-input');
      if (input) input.placeholder = 'सवाल बोलें या लिखें...';
    }

    function toggleLang() {
      const btn = document.getElementById('lang-btn');
      if (activeLanguage === 'hi') {
        activeLanguage = 'en';
        btn.textContent = '🌐 English';
      } else if (activeLanguage === 'en') {
        activeLanguage = 'ta';
        btn.textContent = '🌐 தமிழ்';
      } else {
        activeLanguage = 'hi';
        btn.textContent = '🌐 हिन्दी';
      }
    }

    async function loadHouseholds() {
      try {
        const res = await fetch('/api/households');
        const data = await res.json();
        allHouseholds = data.households || [];
        renderHouseholds(allHouseholds);
      } catch (err) {
        console.error('Failed to load households:', err);
      }
    }

    function renderHouseholds(list) {
      const container = document.getElementById('households-list');
      let high = 0, med = 0, low = 0;

      list.forEach(h => {
        if (h.urgency_tier === 'HIGH') high++;
        else if (h.urgency_tier === 'MEDIUM') med++;
        else low++;
      });
      document.getElementById('stat-high').textContent = high;
      document.getElementById('stat-medium').textContent = med;
      document.getElementById('stat-low').textContent = low;

      if (!list || list.length === 0) {
        container.innerHTML = `
          <div class="empty-placeholder">
            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📋</div>
            <b>डेटाबेस में कोई परिवार दर्ज नहीं है</b><br>
            <span style="font-size: 0.85rem;">नया रिकॉर्ड जुड़ने पर प्राथमिकता सूची स्वतः तैयार होगी।</span>
            <br>
            <button class="btn-action" onclick="refreshPriorities()">सूची ताज़ा करें</button>
          </div>`;
        return;
      }

      container.innerHTML = list.map(h => {
        const tierClass = h.urgency_tier === 'HIGH' ? 'high' : (h.urgency_tier === 'MEDIUM' ? 'medium' : 'low');
        const tierLabel = h.urgency_tier === 'HIGH' ? 'अति आवश्यक' : (h.urgency_tier === 'MEDIUM' ? 'मध्यम' : 'सामान्य');
        const staleness = h.last_visit_date ? `${h.last_visit_date} को भेंट` : 'हाल में कोई भेंट नहीं';

        const reasonsHtml = (h.reasons || []).slice(0, 3).map(r => `
          <div class="reason-chip">
            <span>⚠️</span>
            <span>${r}</span>
          </div>`).join('');

        return `
          <div class="household-card urgency-${tierClass}" onclick="openHouseholdDetail('${h.id}')">
            <div class="card-header">
              <div>
                <div class="household-title">${h.name}</div>
                <div class="household-village">ग्राम: ${h.village || 'रामपुर'} • ${h.income_band || 'सामान्य'}</div>
              </div>
              <span class="tier-badge ${tierClass}">${tierLabel}</span>
            </div>
            <div class="reasons-box">
              ${reasonsHtml}
            </div>
            <div class="card-footer">
              <span>माताएं: ${h.mother_count || 0} • बच्चे: ${h.child_count || 0}</span>
              <span>🕒 ${staleness}</span>
            </div>
          </div>`;
      }).join('');
    }

    function filterCards() {
      const q = document.getElementById('search-input').value.toLowerCase();
      const filtered = allHouseholds.filter(h =>
        (h.name && h.name.toLowerCase().includes(q)) ||
        (h.reasons && h.reasons.some(r => r.toLowerCase().includes(q)))
      );
      renderHouseholds(filtered);
    }

    async function openHouseholdDetail(id) {
      try {
        const res = await fetch(`/api/households/${id}`);
        if (!res.ok) throw new Error('Not found');
        const data = await res.json();
        currentHousehold = data.household;
        renderHouseholdDetail(currentHousehold);
        showView('detail-view');
      } catch (err) {
        alert('परिवार का विवरण लोड करने में त्रुटि: ' + err.message);
      }
    }

    function renderHouseholdDetail(h) {
      const container = document.getElementById('detail-content');
      const tierClass = h.urgency_tier === 'HIGH' ? 'high' : (h.urgency_tier === 'MEDIUM' ? 'medium' : 'low');
      const tierLabel = h.urgency_tier === 'HIGH' ? 'अति आवश्यक' : (h.urgency_tier === 'MEDIUM' ? 'मध्यम' : 'सामान्य');

      // Immunization block
      let immunoHtml = '';
      if (h.children && h.children.length > 0) {
        immunoHtml = h.children.map(c => {
          const doses = c.dose_history || [];
          const dosesList = doses.map(d => {
            const status = d.date_given ? `पूर्ण (${d.date_given})` : (d.due_date ? `देय: ${d.due_date}` : 'लंबित');
            const badgeColor = d.date_given ? 'var(--success)' : 'var(--danger)';
            return `<div class="item-row"><span>${d.vaccine || 'टीका'}</span><b style="color:${badgeColor}">${status}</b></div>`;
          }).join('');
          return `
            <div style="margin-bottom:0.6rem;">
              <div style="font-weight:600;font-size:0.86rem;color:var(--text-muted);margin-bottom:0.2rem;">बच्चा जन्म तिथि: ${c.dob || 'अज्ञात'}</div>
              ${dosesList || '<div style="font-size:0.82rem;color:var(--text-muted);">कोई खुराक दर्ज नहीं</div>'}
            </div>`;
        }).join('');
      } else {
        immunoHtml = '<div style="font-size:0.84rem;color:var(--text-muted);">इस परिवार में कोई पंजीकृत बच्चा नहीं है।</div>';
      }

      // Maternal / ANC block
      let ancHtml = '';
      if (h.mothers && h.mothers.length > 0) {
        ancHtml = h.mothers.map(m => {
          const checkups = m.checkups || [];
          const flags = m.risk_flags || [];
          const checkupRows = checkups.map(chk =>
            `<div class="item-row">
               <span>जांच तिथि: ${chk.date}</span>
               <span>रक्तचाप: <b>${chk.bp || '—'}</b> | Hb: <b>${chk.hb_level ? chk.hb_level + ' g/dL' : '—'}</b></span>
             </div>`
          ).join('');
          return `
            <div style="margin-bottom:0.6rem;">
              <div class="item-row"><span>एएनसी जांच संख्या</span><b>${m.anc_visit_count || 0} जांच</b></div>
              <div class="item-row"><span>अंतिम मासिक धर्म (LMP)</span><b>${m.lmp_date || 'अज्ञात'}</b></div>
              ${flags.length ? `<div class="item-row"><span>जोखिम संकेत</span><b style="color:var(--danger)">${flags.join(', ')}</b></div>` : ''}
              <div style="margin-top:0.4rem;font-size:0.82rem;color:var(--text-muted);">हालिया क्लिनिकल जांच:</div>
              ${checkupRows || '<div style="font-size:0.82rem;color:var(--text-muted);">कोई जांच दर्ज नहीं</div>'}
            </div>`;
        }).join('');
      } else {
        ancHtml = '<div style="font-size:0.84rem;color:var(--text-muted);">इस परिवार में कोई पंजीकृत माता नहीं है।</div>';
      }

      // Schemes block
      let schemesHtml = '';
      if (h.schemes && h.schemes.length > 0) {
        schemesHtml = h.schemes.map(s => `
          <div class="item-row">
            <div>
              <b>${s.scheme_name}</b>
              <div style="font-size:0.75rem;color:var(--text-muted);">${s.reason || ''}</div>
            </div>
            <span class="badge-pill" style="background:var(--primary-light);color:var(--primary-dark);">${s.next_action || 'पात्र'}</span>
          </div>`).join('');
      } else {
        schemesHtml = '<div style="font-size:0.84rem;color:var(--text-muted);">कोई विशेष योजना मिलान दर्ज नहीं है।</div>';
      }

      container.innerHTML = `
        <div class="detail-hero">
          <div class="card-header">
            <div>
              <div class="context-chip">📍 सक्रिय परिवार संदर्भ</div>
              <h2 style="font-size:1.35rem;font-weight:800;">${h.name}</h2>
              <div style="font-size:0.82rem;color:var(--text-muted);margin-top:0.2rem;">
                ग्राम: ${h.village || 'रामपुर'} • श्रेणी: ${h.category || 'सामान्य'} • आय वर्ग: ${h.income_band || 'मध्यम'}
              </div>
            </div>
            <span class="tier-badge ${tierClass}">${tierLabel} (स्कोर: ${h.score})</span>
          </div>
          <button class="btn-action" style="width:100%;justify-content:center;margin-top:0.8rem;" onclick="openVoiceAssistantWithContext('${h.id}', '${h.name}')">
            🎙️ इस परिवार के स्वास्थ्य पर सवाल पूछें
          </button>
        </div>

        <div class="module-card">
          <div class="module-header">
            <div class="module-title"><span>💉</span> टीकाकरण स्थिति (UIP Schedule)</div>
          </div>
          ${immunoHtml}
        </div>

        <div class="module-card">
          <div class="module-header">
            <div class="module-title"><span>🤰</span> मातृ स्वास्थ्य एवं ANC जांच</div>
          </div>
          ${ancHtml}
        </div>

        <div class="module-card">
          <div class="module-header">
            <div class="module-title"><span>🏛️</span> सरकारी योजना पात्रता (Schemes)</div>
          </div>
          ${schemesHtml}
        </div>
      `;
    }

    function showView(viewId) {
      document.querySelectorAll('.view').forEach(el => el.classList.remove('active'));
      document.getElementById(viewId).classList.add('active');
    }

    async function refreshPriorities() {
      try {
        const res = await fetch('/api/prioritize/refresh', { method: 'POST' });
        const data = await res.json();
        allHouseholds = data.households || [];
        renderHouseholds(allHouseholds);
      } catch (err) {
        console.error('Refresh error:', err);
      }
    }

    /* ⭐ Multi-turn Voice Overlay System */
    function openVoiceAssistant() {
      currentHousehold = null;
      document.getElementById('voice-title').textContent = 'सहया संवाद सहायक';
      document.getElementById('voice-context-pill').textContent = '📍 सामान्य प्रोटोकॉल मोड';
      document.getElementById('voice-sheet').style.display = 'flex';
    }

    function openVoiceAssistantWithContext(hhId, hhName) {
      document.getElementById('voice-title').textContent = 'सहया संवाद सहायक';
      document.getElementById('voice-context-pill').textContent = `📍 संदर्भ: ${hhName} का परिवार`;
      document.getElementById('voice-sheet').style.display = 'flex';
    }

    function closeVoiceAssistant() {
      document.getElementById('voice-sheet').style.display = 'none';
      stopListening();
    }

    function resetConversation() {
      conversationBuffer = [];
      const stream = document.getElementById('chat-stream');
      stream.innerHTML = `
        <div class="chat-bubble assistant">
          नमस्ते! बातचीत रीसेट कर दी गई है। आप नया सवाल पूछ सकते हैं।
        </div>`;
      document.getElementById('followup-listening-indicator').style.display = 'none';
    }

    function askQuick(text) {
      document.getElementById('voice-text-input').value = text;
      sendQuestion();
    }

    async function sendQuestion() {
      const input = document.getElementById('voice-text-input');
      const query = input.value.trim();
      if (!query) return;

      input.value = '';
      const stream = document.getElementById('chat-stream');
      document.getElementById('followup-listening-indicator').style.display = 'none';

      // 1. Append User Bubble
      const userBubble = document.createElement('div');
      userBubble.className = 'chat-bubble user';
      userBubble.textContent = query;
      stream.appendChild(userBubble);
      stream.scrollTop = stream.scrollHeight;

      // 2. Append Pending Assistant Bubble
      const assistantBubble = document.createElement('div');
      assistantBubble.className = 'chat-bubble assistant';
      assistantBubble.innerHTML = '<i>सहया प्रोटोकॉल खोज रहा है एवं उत्तर तैयार कर रहा है...</i>';
      stream.appendChild(assistantBubble);
      stream.scrollTop = stream.scrollHeight;

      try {
        const payload = {
          query: query,
          conversation: conversationBuffer,
          household_id: currentHousehold ? currentHousehold.id : null
        };

        const res = await fetch('/api/ask', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.error) {
          assistantBubble.innerHTML = `<b style="color:var(--danger)">त्रुटि:</b> ${data.error}`;
        } else {
          // Render grounded answer
          const sources = (data.source_chunks || []).map(s =>
            `<div class="citation-tag"><b>[${s.id}]</b> ${s.title} (${s.authority || 'MoHFW'})<br>${s.excerpt}</div>`
          ).join('');

          assistantBubble.innerHTML = `
            <div>${data.answer}</div>
            <div class="confidence-badge">✓ आत्मविश्वास स्कोर: ${data.confidence}</div>
            ${sources ? `<div style="margin-top:0.4rem;font-weight:700;font-size:0.75rem;color:var(--text-muted);">आधिकारिक स्रोत उद्धरण:</div>${sources}` : ''}
            <div style="margin-top:0.5rem;">
              <button class="badge-pill" style="background:var(--surface-subtle);color:var(--primary);border:1px solid var(--border);" onclick="speakAnswer('${data.answer.replace(/'/g, "\\'")}')">🔊 उत्तर सुनें</button>
            </div>
          `;

          // Add to conversation buffer (last 2 turns)
          conversationBuffer.push({ query: query, answer: data.answer });
          if (conversationBuffer.length > 2) conversationBuffer.shift();

          // Auto-read aloud if speech synthesis is available
          speakAnswer(data.answer);

          // ⭐ Show Ambient Follow-up Listening Cue
          showFollowupCue();
        }
      } catch (err) {
        assistantBubble.innerHTML = `<b style="color:var(--danger)">कनेक्शन त्रुटि:</b> ${err.message}`;
      }

      stream.scrollTop = stream.scrollHeight;
    }

    function speakAnswer(text) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = activeLanguage === 'ta' ? 'ta-IN' : (activeLanguage === 'en' ? 'en-IN' : 'hi-IN');
        window.speechSynthesis.speak(utterance);
      }
    }

    function showFollowupCue() {
      const cue = document.getElementById('followup-listening-indicator');
      cue.style.display = 'flex';
      cue.scrollIntoView({ behavior: 'smooth' });
    }

    // Initial load
    loadHouseholds();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict | list, status: int = HTTPStatus.OK):
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            payload = PAGE_HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if self.path == "/api/households":
            with sqlite3.connect(DB_PATH) as conn:
                households = PRIORITIZER.get_prioritized_households(conn)
            self._send_json({"households": households})
            return

        if self.path.startswith("/api/households/"):
            hh_id = self.path[len("/api/households/"):].strip()
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, village, income_band, category, contact_notes FROM households WHERE id = ?",
                    (hh_id,),
                )
                hh_row = cursor.fetchone()
                if not hh_row:
                    self._send_json({"error": "Household not found"}, HTTPStatus.NOT_FOUND)
                    return

                res = PRIORITIZER.evaluate_household(hh_id, conn)

                # Fetch mothers and ANC checkups
                cursor.execute(
                    "SELECT id, age, lmp_date, anc_visit_count, risk_flags_json, last_visit_date FROM mothers WHERE household_id = ?",
                    (hh_id,),
                )
                mothers_data = []
                for m_id, m_age, lmp, anc_cnt, flags_raw, last_v in cursor.fetchall():
                    cursor.execute(
                        "SELECT id, date, bp, hb_level, danger_signs_json, notes FROM anc_checkups WHERE mother_id = ? ORDER BY date DESC",
                        (m_id,),
                    )
                    chk_list = []
                    for c_id, c_dt, c_bp, c_hb, c_danger, c_notes in cursor.fetchall():
                        chk_list.append({
                            "id": c_id, "date": c_dt, "bp": c_bp, "hb_level": c_hb,
                            "danger_signs": json.loads(c_danger) if c_danger else [], "notes": c_notes
                        })
                    mothers_data.append({
                        "id": m_id, "age": m_age, "lmp_date": lmp, "anc_visit_count": anc_cnt,
                        "risk_flags": json.loads(flags_raw) if flags_raw else [],
                        "last_visit_date": last_v, "checkups": chk_list
                    })

                # Fetch children and dose history
                cursor.execute(
                    "SELECT id, dob, dose_history_json FROM children WHERE household_id = ?",
                    (hh_id,),
                )
                children_data = []
                for c_id, c_dob, dose_raw in cursor.fetchall():
                    children_data.append({
                        "id": c_id, "dob": c_dob,
                        "dose_history": json.loads(dose_raw) if dose_raw else []
                    })

                # Fetch scheme matches
                cursor.execute(
                    "SELECT scheme_name, eligible, reason, next_action FROM scheme_matches WHERE household_id = ?",
                    (hh_id,),
                )
                schemes_data = []
                for s_name, el, rsn, act in cursor.fetchall():
                    schemes_data.append({
                        "scheme_name": s_name, "eligible": bool(el),
                        "reason": rsn, "next_action": act
                    })

            household_dict = {
                "id": hh_row[0],
                "name": hh_row[1],
                "village": hh_row[2],
                "income_band": hh_row[3],
                "category": hh_row[4],
                "contact_notes": hh_row[5],
                "score": res.score if res else 0.0,
                "urgency_tier": res.urgency_tier if res else "LOW",
                "reasons": res.reasons if res else [],
                "mothers": mothers_data,
                "children": children_data,
                "schemes": schemes_data,
            }
            self._send_json({"household": household_dict})
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if self.path == "/api/prioritize/refresh":
            with sqlite3.connect(DB_PATH) as conn:
                PRIORITIZER.refresh_priority_queue(conn)
                households = PRIORITIZER.get_prioritized_households(conn)
            self._send_json({"success": True, "households": households})
            return

        if self.path == "/api/ask":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                data = json.loads(self.rfile.read(size))
                query = data.get("query", "").strip()
                conversation = data.get("conversation") or []
                household_id = data.get("household_id")

                # If a specific household context is active, enrich retrieval context with clinical flags
                if household_id:
                    with sqlite3.connect(DB_PATH) as conn:
                        res = PRIORITIZER.evaluate_household(household_id, conn)
                        if res and res.reasons:
                            # Attach household context terms to guide retrieval if relevant
                            query_with_context = f"{query} {' '.join(res.reasons[:2])}"
                            response = PIPELINE.answer(query_with_context, conversation=conversation)
                        else:
                            response = PIPELINE.answer(query, conversation=conversation)
                else:
                    response = PIPELINE.answer(query, conversation=conversation)

                self._send_json(response, HTTPStatus.OK)
            except (ValueError, InferenceUnavailable) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.UNPROCESSABLE_ENTITY)
            return

        if self.path == "/api/voice/transcribe":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                audio_bytes = self.rfile.read(size)
                result = TRANSCRIBER.transcribe_audio_bytes(audio_bytes)
                self._send_json(result, HTTPStatus.OK)
            except (ValueError, AsrUnavailable) as exc:
                self._send_json({"error": str(exc)}, HTTPStatus.UNPROCESSABLE_ENTITY)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print("Sahaya Field Assistant server running on http://127.0.0.1:8080")
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()
