DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EKIP - Enterprise Knowledge Intelligence Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @keyframes pulse-subtle { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
    .streaming-pulse { animation: pulse-subtle 1.2s infinite; }
    .custom-scrollbar::-webkit-scrollbar { width: 6px; height: 6px; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #374151; border-radius: 3px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: #111827; }
  </style>
</head>
<body class="bg-gray-950 text-gray-100 font-sans min-h-screen flex flex-col">

  <!-- TOP HEADER -->
  <header class="border-b border-gray-800 bg-gray-900/90 backdrop-blur sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between shadow-md">
    <div class="flex items-center space-x-3">
      <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
        <i class="fa-solid fa-brain text-lg"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-white flex items-center gap-2">
          EKIP <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">v0.1.0 Enterprise</span>
        </h1>
        <p class="text-xs text-gray-400">Enterprise Knowledge Intelligence Platform (100% Free & Local)</p>
      </div>
    </div>

    <!-- NAVIGATION TABS -->
    <nav class="hidden md:flex space-x-1 bg-gray-950/60 p-1 rounded-xl border border-gray-800">
      <button onclick="switchTab('chat')" id="tab-btn-chat" class="tab-btn px-4 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 bg-indigo-600 text-white shadow-sm flex items-center gap-2">
        <i class="fa-solid fa-comments"></i> RAG Chat Assistant
      </button>
      <button onclick="switchTab('documents')" id="tab-btn-documents" class="tab-btn px-4 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 flex items-center gap-2">
        <i class="fa-solid fa-folder-open"></i> Documents & Queue
      </button>
      <button onclick="switchTab('analytics')" id="tab-btn-analytics" class="tab-btn px-4 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 flex items-center gap-2">
        <i class="fa-solid fa-chart-line"></i> Analytics & Observability
      </button>
    </nav>

    <!-- AUTH BAR -->
    <div class="flex items-center space-x-3">
      <div id="user-pill" class="hidden items-center gap-2 bg-gray-800/80 px-3 py-1.5 rounded-lg border border-gray-700 text-xs">
        <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
        <span id="tenant-display" class="font-semibold text-gray-200">Tenant</span>
        <span id="role-badge" class="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/20 text-indigo-300 font-mono">admin</span>
        <button onclick="logout()" class="text-gray-400 hover:text-red-400 ml-2" title="Sign out"><i class="fa-solid fa-right-from-bracket"></i></button>
      </div>
      <button id="login-modal-btn" onclick="openAuthModal()" class="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow transition">
        <i class="fa-solid fa-user-lock mr-1"></i> Sign In / Register
      </button>
    </div>
  </header>

  <!-- MAIN VIEW CONTAINER -->
  <main class="flex-1 flex overflow-hidden">

    <!-- ========================================== -->
    <!-- TAB 1: RAG CHAT ASSISTANT -->
    <!-- ========================================== -->
    <section id="view-chat" class="flex-1 flex overflow-hidden">
      <!-- SIDEBAR CONTROLS -->
      <aside class="w-80 border-r border-gray-800 bg-gray-900/50 p-5 flex flex-col justify-between overflow-y-auto custom-scrollbar">
        <div class="space-y-5">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Knowledge Collection</label>
            <select id="chat-collection-select" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500 transition">
              <option value="">Loading collections...</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Query Transformation</label>
            <select id="chat-strategy-select" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500 transition">
              <option value="none">None (Standard Hybrid RRF)</option>
              <option value="hyde">HyDE (Hypothetical Doc Embedding)</option>
              <option value="expansion">Multi-Query Expansion</option>
              <option value="rewrite">Query Rewriter</option>
            </select>
            <p class="text-[11px] text-gray-500 mt-1">Enhances search recall via zero-cost query reformulations.</p>
          </div>

          <div class="border-t border-gray-800 pt-4 space-y-3">
            <div class="flex items-center justify-between">
              <label class="text-xs font-medium text-gray-300">Real-Time Streaming (SSE)</label>
              <input type="checkbox" id="chat-stream-toggle" checked class="accent-indigo-600 w-4 h-4 cursor-pointer">
            </div>
            <div class="flex items-center justify-between">
              <label class="text-xs font-medium text-gray-300">Cross-Encoder Reranking</label>
              <input type="checkbox" id="chat-rerank-toggle" checked class="accent-indigo-600 w-4 h-4 cursor-pointer">
            </div>
            <div class="flex items-center justify-between">
              <label class="text-xs font-medium text-gray-300">Sentence Compression</label>
              <input type="checkbox" id="chat-compress-toggle" checked class="accent-indigo-600 w-4 h-4 cursor-pointer">
            </div>
          </div>
        </div>

        <div class="border-t border-gray-800 pt-4 text-[11px] text-gray-500 space-y-1">
          <div class="flex justify-between"><span>Vector Embeddings:</span> <span class="text-gray-300 font-mono">1024-d (FastEmbed)</span></div>
          <div class="flex justify-between"><span>Reranker:</span> <span class="text-gray-300 font-mono">bge-reranker (CPU)</span></div>
          <div class="flex justify-between"><span>Inference Cost:</span> <span class="text-emerald-400 font-mono">$0.00 / query</span></div>
        </div>
      </aside>

      <!-- CHAT MESSAGE CANVAS -->
      <div class="flex-1 flex flex-col bg-gray-950">
        <!-- MESSAGES LIST -->
        <div id="chat-messages" class="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
          <div class="flex gap-3 text-sm max-w-3xl">
            <div class="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <i class="fa-solid fa-robot"></i>
            </div>
            <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 text-gray-200 space-y-2">
              <p class="font-medium text-white">Hello! I am your Enterprise Knowledge Assistant.</p>
              <p class="text-xs text-gray-400 leading-relaxed">
                I answer questions strictly grounded in your enterprise knowledge collections, complete with verified citations, real-time RAG Triad hallucination guardrails, and zero hallucination guarantee.
              </p>
            </div>
          </div>
        </div>

        <!-- CHAT INPUT COMPONENT -->
        <div class="p-4 border-t border-gray-800 bg-gray-900/40">
          <form onsubmit="handleSendQuery(event)" class="max-w-4xl mx-auto flex gap-3">
            <input type="text" id="chat-input" placeholder="Ask a question about your enterprise documents..." 
                   class="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition">
            <button type="submit" id="send-btn" class="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition flex items-center gap-2">
              <span>Send</span> <i class="fa-solid fa-paper-plane text-xs"></i>
            </button>
          </form>
        </div>
      </div>
    </section>

    <!-- ========================================== -->
    <!-- TAB 2: DOCUMENTS & BACKGROUND QUEUE -->
    <!-- ========================================== -->
    <section id="view-documents" class="hidden flex-1 overflow-y-auto p-8 bg-gray-950 custom-scrollbar">
      <div class="max-w-6xl mx-auto space-y-8">
        <!-- TOP ACTIONS & STATS -->
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl font-bold text-white">Knowledge Ingestion & Queue</h2>
            <p class="text-xs text-gray-400 mt-1">Upload enterprise documents into isolated collections with structural chunking and async background queues.</p>
          </div>
          <button onclick="openCreateCollectionModal()" class="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow flex items-center gap-2">
            <i class="fa-solid fa-plus"></i> New Collection
          </button>
        </div>

        <!-- UPLOAD DROPZONE -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="md:col-span-2 bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
            <h3 class="text-sm font-semibold text-gray-200 mb-4 flex items-center gap-2">
              <i class="fa-solid fa-cloud-arrow-up text-indigo-400"></i> Document Ingestion Dropzone
            </h3>
            
            <form id="upload-form" onsubmit="handleUploadDocument(event)" class="space-y-4">
              <div>
                <label class="block text-xs font-medium text-gray-400 mb-1">Target Knowledge Collection</label>
                <select id="upload-collection-select" required class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs text-gray-200 focus:outline-none focus:border-indigo-500">
                  <option value="">Select a collection...</option>
                </select>
              </div>

              <!-- DRAG DROP AREA -->
              <div id="drop-area" class="border-2 border-dashed border-gray-700 hover:border-indigo-500 rounded-xl p-8 text-center cursor-pointer transition bg-gray-950/40"
                   onclick="document.getElementById('file-input').click()">
                <input type="file" id="file-input" class="hidden" accept=".pdf,.md,.txt">
                <i class="fa-solid fa-file-arrow-up text-3xl text-gray-500 mb-3"></i>
                <p id="file-chosen-text" class="text-xs text-gray-300 font-medium">Click to browse or drag and drop files here</p>
                <p class="text-[11px] text-gray-500 mt-1">Supports Markdown (.md), PDF (.pdf), Text (.txt) up to 50 MB</p>
              </div>

              <div class="flex items-center justify-between pt-2">
                <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
                  <input type="checkbox" id="upload-async-toggle" checked class="accent-indigo-600 w-4 h-4">
                  <span>Asynchronous Background Queue (Redis)</span>
                </label>
                <button type="submit" id="upload-submit-btn" class="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow transition">
                  Ingest Document
                </button>
              </div>
            </form>
          </div>

          <!-- ACTIVE JOB PROGRESS PANEL -->
          <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-6 flex flex-col justify-between">
            <div>
              <h3 class="text-sm font-semibold text-gray-200 mb-2 flex items-center gap-2">
                <i class="fa-solid fa-gears text-indigo-400"></i> Active Task Worker
              </h3>
              <p class="text-xs text-gray-400 mb-4">Background Redis queue task monitor.</p>
              
              <div id="active-job-box" class="hidden bg-gray-950 border border-gray-800 rounded-xl p-4 space-y-3">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-semibold text-gray-200" id="job-doc-name">Document</span>
                  <span id="job-status-pill" class="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">queued</span>
                </div>
                <div class="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
                  <div id="job-progress-bar" class="bg-indigo-600 h-2 transition-all duration-300" style="width: 0%"></div>
                </div>
                <div class="flex justify-between text-[11px] text-gray-400">
                  <span id="job-stage-text">Stage: queued</span>
                  <span id="job-progress-text">0%</span>
                </div>
              </div>

              <div id="no-active-job" class="text-center py-8 text-gray-500 text-xs">
                No active ingestion jobs currently running.
              </div>
            </div>

            <div class="text-[11px] text-gray-500 pt-4 border-t border-gray-800">
              <span class="text-emerald-400"><i class="fa-solid fa-circle-check"></i> Ingestion Engine Ready</span> (Structural chunking with contextual path headers).
            </div>
          </div>
        </div>

        <!-- INGESTED DOCUMENTS TABLE -->
        <div class="bg-gray-900/60 border border-gray-800 rounded-2xl overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-800 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-white">Ingested Document Repository</h3>
            <button onclick="loadDocumentsList()" class="text-xs text-gray-400 hover:text-gray-200"><i class="fa-solid fa-rotate-right mr-1"></i> Refresh</button>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-gray-950/60 text-gray-400 uppercase tracking-wider font-semibold border-b border-gray-800">
                <tr>
                  <th class="px-6 py-3">Document Title</th>
                  <th class="px-6 py-3">MIME Type</th>
                  <th class="px-6 py-3">Content Hash</th>
                  <th class="px-6 py-3">Status</th>
                  <th class="px-6 py-3">Created</th>
                </tr>
              </thead>
              <tbody id="documents-table-body" class="divide-y divide-gray-800 text-gray-300">
                <tr><td colspan="5" class="px-6 py-6 text-center text-gray-500">Loading documents...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- ========================================== -->
    <!-- TAB 3: ANALYTICS & OBSERVABILITY -->
    <!-- ========================================== -->
    <section id="view-analytics" class="hidden flex-1 overflow-y-auto p-8 bg-gray-950 custom-scrollbar">
      <div class="max-w-6xl mx-auto space-y-8">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-xl font-bold text-white">System Telemetry & Observability</h2>
            <p class="text-xs text-gray-400 mt-1">Real-time telemetry, cache hit efficiency, LLM costs, and RAG Triad quality metrics.</p>
          </div>
          <button onclick="loadAnalyticsOverview()" class="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-semibold text-gray-200 border border-gray-700 shadow flex items-center gap-2">
            <i class="fa-solid fa-arrows-rotate"></i> Refresh Telemetry
          </button>
        </div>

        <!-- 6 KPI METRIC CARDS -->
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <div class="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <span class="text-[11px] font-medium text-gray-400">Total Queries</span>
            <p id="kpi-queries" class="text-xl font-bold text-white mt-1">0</p>
          </div>
          <div class="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <span class="text-[11px] font-medium text-gray-400">Cache Hit Rate</span>
            <p id="kpi-cache-rate" class="text-xl font-bold text-emerald-400 mt-1">0.0%</p>
          </div>
          <div class="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <span class="text-[11px] font-medium text-gray-400">Average Latency</span>
            <p id="kpi-latency" class="text-xl font-bold text-indigo-400 mt-1">0 ms</p>
          </div>
          <div class="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <span class="text-[11px] font-medium text-gray-400">Total Cost</span>
            <p id="kpi-cost" class="text-xl font-bold text-emerald-400 mt-1">$0.0000</p>
          </div>
          <div class="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <span class="text-[11px] font-medium text-gray-400">Hallucination Rate</span>
            <p id="kpi-hallucination" class="text-xl font-bold text-amber-400 mt-1">0.0%</p>
          </div>
          <div class="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
            <span class="text-[11px] font-medium text-gray-400">User Satisfaction</span>
            <p id="kpi-satisfaction" class="text-xl font-bold text-violet-400 mt-1">100%</p>
          </div>
        </div>

        <!-- RAG TRIAD QUALITY AUDIT -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-semibold text-gray-300">Groundedness (Faithfulness)</span>
              <span id="score-groundedness" class="text-sm font-bold text-emerald-400 font-mono">1.00</span>
            </div>
            <div class="w-full bg-gray-800 rounded-full h-2 mb-2">
              <div id="bar-groundedness" class="bg-emerald-500 h-2 rounded-full" style="width: 100%"></div>
            </div>
            <p class="text-[11px] text-gray-400">Verifies that claims in the answer are strictly supported by retrieved context.</p>
          </div>

          <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-semibold text-gray-300">Context Relevance</span>
              <span id="score-context" class="text-sm font-bold text-indigo-400 font-mono">1.00</span>
            </div>
            <div class="w-full bg-gray-800 rounded-full h-2 mb-2">
              <div id="bar-context" class="bg-indigo-500 h-2 rounded-full" style="width: 100%"></div>
            </div>
            <p class="text-[11px] text-gray-400">Measures lexical & semantic alignment between user question and chunks.</p>
          </div>

          <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
            <div class="flex items-center justify-between mb-3">
              <span class="text-xs font-semibold text-gray-300">Answer Relevance</span>
              <span id="score-answer" class="text-sm font-bold text-violet-400 font-mono">1.00</span>
            </div>
            <div class="w-full bg-gray-800 rounded-full h-2 mb-2">
              <div id="bar-answer" class="bg-violet-500 h-2 rounded-full" style="width: 100%"></div>
            </div>
            <p class="text-[11px] text-gray-400">Ensures the generated answer directly addresses the user query.</p>
          </div>
        </div>

        <!-- MODEL CONSUMPTION BREAKDOWN -->
        <div class="bg-gray-900/60 border border-gray-800 rounded-2xl p-6">
          <h3 class="text-sm font-semibold text-white mb-4">Model Cost & Distribution Breakdown</h3>
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-gray-950/60 text-gray-400 uppercase tracking-wider font-semibold border-b border-gray-800">
                <tr>
                  <th class="px-6 py-3">Model / Source</th>
                  <th class="px-6 py-3">Executions</th>
                  <th class="px-6 py-3">Cumulative Cost</th>
                  <th class="px-6 py-3">Efficiency</th>
                </tr>
              </thead>
              <tbody id="models-table-body" class="divide-y divide-gray-800 text-gray-300">
                <tr><td colspan="4" class="px-6 py-6 text-center text-gray-500">No query data recorded yet</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- ========================================== -->
  <!-- MODALS -->
  <!-- ========================================== -->
  <!-- AUTH MODAL -->
  <div id="auth-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-base font-bold text-white">Enterprise Authentication</h3>
        <button onclick="closeAuthModal()" class="text-gray-400 hover:text-gray-200"><i class="fa-solid fa-xmark"></i></button>
      </div>
      
      <div class="flex border-b border-gray-800 text-xs font-semibold">
        <button id="auth-tab-login" onclick="setAuthMode('login')" class="flex-1 py-2 text-indigo-400 border-b-2 border-indigo-500">Login</button>
        <button id="auth-tab-register" onclick="setAuthMode('register')" class="flex-1 py-2 text-gray-400">Register Tenant</button>
      </div>

      <form id="auth-form" onsubmit="handleAuthSubmit(event)" class="space-y-3 text-xs">
        <div id="tenant-field" class="hidden">
          <label class="block text-gray-400 mb-1">Tenant Organization Name</label>
          <input type="text" id="auth-tenant" placeholder="Acme Corporation" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white">
        </div>
        <div>
          <label class="block text-gray-400 mb-1">Work Email</label>
          <input type="email" id="auth-email" required placeholder="admin@enterprise.com" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white">
        </div>
        <div>
          <label class="block text-gray-400 mb-1">Password</label>
          <input type="password" id="auth-password" required placeholder="••••••••••••" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white">
        </div>

        <button type="submit" class="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow transition mt-2">
          Authenticate
        </button>

        <button type="button" onclick="fillDemoCredentials()" class="w-full py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 font-medium transition">
          ⚡ Auto-Create Demo Admin
        </button>
      </form>
    </div>
  </div>

  <!-- CREATE COLLECTION MODAL -->
  <div id="collection-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-sm shadow-2xl space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-white">Create Knowledge Collection</h3>
        <button onclick="closeCreateCollectionModal()" class="text-gray-400 hover:text-gray-200"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleCreateCollection(event)" class="space-y-3 text-xs">
        <div>
          <label class="block text-gray-400 mb-1">Collection Name</label>
          <input type="text" id="new-collection-name" required placeholder="e.g. Engineering Runbooks" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white">
        </div>
        <button type="submit" class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow transition">
          Create Collection
        </button>
      </form>
    </div>
  </div>

  <!-- FEEDBACK MODAL -->
  <div id="feedback-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
    <div class="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full max-w-sm shadow-2xl space-y-4">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-bold text-white">Response Feedback</h3>
        <button onclick="closeFeedbackModal()" class="text-gray-400 hover:text-gray-200"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleSubmitFeedback(event)" class="space-y-3 text-xs">
        <input type="hidden" id="feedback-query-id">
        <input type="hidden" id="feedback-is-helpful">

        <div>
          <label class="block text-gray-400 mb-1">Rating (1 to 5 Stars)</label>
          <select id="feedback-rating" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white">
            <option value="5">⭐⭐⭐⭐⭐ Excellent (5)</option>
            <option value="4">⭐⭐⭐⭐ Good (4)</option>
            <option value="3">⭐⭐⭐ Neutral (3)</option>
            <option value="2">⭐⭐ Poor (2)</option>
            <option value="1">⭐ Inaccurate / Bad (1)</option>
          </select>
        </div>

        <div>
          <label class="block text-gray-400 mb-1">Category</label>
          <select id="feedback-category" class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white">
            <option value="general">General Feedback</option>
            <option value="hallucination">Hallucination Detected</option>
            <option value="missing_info">Missing Key Information</option>
            <option value="incorrect_citation">Incorrect Citation</option>
            <option value="unhelpful">Unhelpful Response</option>
          </select>
        </div>

        <div>
          <label class="block text-gray-400 mb-1">Comment (Optional)</label>
          <textarea id="feedback-comment" rows="3" placeholder="Tell us what could be improved..." class="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"></textarea>
        </div>

        <button type="submit" class="w-full py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow transition">
          Submit Feedback
        </button>
      </form>
    </div>
  </div>

  <!-- JAVASCRIPT LOGIC -->
  <script>
    let authToken = localStorage.getItem('ekip_token') || null;
    let authTenant = localStorage.getItem('ekip_tenant') || null;
    let authRole = localStorage.getItem('ekip_role') || null;
    let authMode = 'login';
    let pollingInterval = null;

    // Initialize UI on load
    document.addEventListener('DOMContentLoaded', () => {
      checkAuthStatus();
      if (authToken) {
        loadCollections();
        loadDocumentsList();
        loadAnalyticsOverview();
      }
    });

    function checkAuthStatus() {
      const userPill = document.getElementById('user-pill');
      const loginBtn = document.getElementById('login-modal-btn');
      if (authToken) {
        userPill.classList.remove('hidden');
        userPill.classList.add('flex');
        loginBtn.classList.add('hidden');
        document.getElementById('tenant-display').innerText = authTenant || 'Enterprise';
        document.getElementById('role-badge').innerText = authRole || 'admin';
      } else {
        userPill.classList.add('hidden');
        userPill.classList.remove('flex');
        loginBtn.classList.remove('hidden');
      }
    }

    function switchTab(tabId) {
      ['chat', 'documents', 'analytics'].forEach(tab => {
        const view = document.getElementById(`view-${tab}`);
        const btn = document.getElementById(`tab-btn-${tab}`);
        if (tab === tabId) {
          view.classList.remove('hidden');
          if (tab === 'chat') view.classList.add('flex');
          btn.className = 'tab-btn px-4 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 bg-indigo-600 text-white shadow-sm flex items-center gap-2';
        } else {
          view.classList.add('hidden');
          view.classList.remove('flex');
          btn.className = 'tab-btn px-4 py-1.5 text-xs font-medium rounded-lg transition-all duration-200 text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 flex items-center gap-2';
        }
      });
      if (tabId === 'documents') loadDocumentsList();
      if (tabId === 'analytics') loadAnalyticsOverview();
    }

    // AUTH FUNCTIONS
    function openAuthModal() { document.getElementById('auth-modal').classList.remove('hidden'); }
    function closeAuthModal() { document.getElementById('auth-modal').classList.add('hidden'); }
    function setAuthMode(mode) {
      authMode = mode;
      const tenantField = document.getElementById('tenant-field');
      const loginTab = document.getElementById('auth-tab-login');
      const registerTab = document.getElementById('auth-tab-register');
      if (mode === 'register') {
        tenantField.classList.remove('hidden');
        registerTab.className = 'flex-1 py-2 text-indigo-400 border-b-2 border-indigo-500';
        loginTab.className = 'flex-1 py-2 text-gray-400';
      } else {
        tenantField.classList.add('hidden');
        loginTab.className = 'flex-1 py-2 text-indigo-400 border-b-2 border-indigo-500';
        registerTab.className = 'flex-1 py-2 text-gray-400';
      }
    }

    async function fillDemoCredentials() {
      const suffix = Math.random().toString(36).substring(2, 7);
      const email = `admin_${suffix}@enterprise.com`;
      const password = 'SecurePassword123!';
      const tenant = `Enterprise_${suffix}`;

      try {
        const res = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ email, password, role: 'admin', tenant_name: tenant })
        });
        const data = await res.json();
        const loginRes = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ email, password })
        });
        const loginData = await loginRes.json();
        saveAuthSession(loginData.access_token, tenant, 'admin');
        closeAuthModal();
        loadCollections();
      } catch (err) {
        alert('Auto-register failed: ' + err.message);
      }
    }

    async function handleAuthSubmit(e) {
      e.preventDefault();
      const email = document.getElementById('auth-email').value;
      const password = document.getElementById('auth-password').value;
      const tenant = document.getElementById('auth-tenant').value;

      try {
        if (authMode === 'register') {
          await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email, password, role: 'admin', tenant_name: tenant || 'Enterprise' })
          });
        }
        const res = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ email, password })
        });
        if (!res.ok) throw new Error('Invalid credentials');
        const data = await res.json();
        saveAuthSession(data.access_token, tenant || 'Enterprise', 'admin');
        closeAuthModal();
        loadCollections();
      } catch (err) {
        alert('Authentication failed: ' + err.message);
      }
    }

    function saveAuthSession(token, tenant, role) {
      authToken = token;
      authTenant = tenant;
      authRole = role;
      localStorage.setItem('ekip_token', token);
      localStorage.setItem('ekip_tenant', tenant);
      localStorage.setItem('ekip_role', role);
      checkAuthStatus();
    }

    function logout() {
      localStorage.clear();
      authToken = null;
      checkAuthStatus();
      location.reload();
    }

    // COLLECTIONS
    async function loadCollections() {
      if (!authToken) return;
      try {
        const res = await fetch('/api/v1/collections', {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const collections = await res.json();
        const selects = [document.getElementById('chat-collection-select'), document.getElementById('upload-collection-select')];
        selects.forEach(select => {
          select.innerHTML = collections.length === 0 
            ? '<option value="">No collections found - please create one</option>' 
            : collections.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        });
      } catch (e) {
        console.error('Failed to load collections', e);
      }
    }

    function openCreateCollectionModal() { document.getElementById('collection-modal').classList.remove('hidden'); }
    function closeCreateCollectionModal() { document.getElementById('collection-modal').classList.add('hidden'); }

    async function handleCreateCollection(e) {
      e.preventDefault();
      const name = document.getElementById('new-collection-name').value;
      try {
        const res = await fetch('/api/v1/collections', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
          body: JSON.stringify({ name })
        });
        if (!res.ok) throw new Error('Failed to create collection');
        closeCreateCollectionModal();
        document.getElementById('new-collection-name').value = '';
        await loadCollections();
      } catch (err) {
        alert(err.message);
      }
    }

    // CHAT & STREAMING PIPELINE
    async function handleSendQuery(e) {
      e.preventDefault();
      const input = document.getElementById('chat-input');
      const query = input.value.trim();
      if (!query || !authToken) {
        if (!authToken) openAuthModal();
        return;
      }

      const collectionId = document.getElementById('chat-collection-select').value;
      if (!collectionId) {
        alert('Please create and select a knowledge collection first');
        return;
      }

      const strategy = document.getElementById('chat-strategy-select').value;
      const isStreaming = document.getElementById('chat-stream-toggle').checked;
      const rerank = document.getElementById('chat-rerank-toggle').checked;
      const compress = document.getElementById('chat-compress-toggle').checked;

      // Append User Message
      appendUserMessage(query);
      input.value = '';

      // Prepare Assistant Box
      const assistantMessageId = 'msg-' + Math.random().toString(36).substring(2, 9);
      const assistantBox = appendAssistantSkeleton(assistantMessageId);

      try {
        if (isStreaming) {
          // SSE STREAMING
          const response = await fetch('/api/v1/query/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify({ query, collection_ids: [collectionId], query_transformation: strategy, rerank, compress_context: compress })
          });

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let currentEvent = null;
          let answerText = '';
          let sources = [];

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value);
            const lines = chunk.split('\\n');

            for (const line of lines) {
              if (line.startsWith('event: ')) {
                currentEvent = line.replace('event: ', '').trim();
              } else if (line.startsWith('data: ')) {
                const dataStr = line.replace('data: ', '').trim();
                if (currentEvent === 'sources') {
                  try { sources = JSON.parse(dataStr); } catch (_) {}
                } else if (currentEvent === 'token') {
                  let tokenText = dataStr;
                  try {
                    const parsed = JSON.parse(dataStr);
                    if (parsed && parsed.text !== undefined) {
                      tokenText = parsed.text;
                    }
                  } catch (_) {}
                  answerText += tokenText;
                  updateAssistantText(assistantMessageId, answerText);
                } else if (currentEvent === 'abstention') {
                  try {
                    const absData = JSON.parse(dataStr);
                    answerText = absData.message || 'I do not have enough information in the provided documents to answer this question.';
                  } catch (_) {
                    answerText = 'I do not have enough information in the provided documents to answer this question.';
                  }
                  finalizeAssistantMessage(assistantMessageId, answerText, [], { abstained: true, groundedness_score: 1.0 });
                } else if (currentEvent === 'done') {
                  try {
                    const doneMeta = JSON.parse(dataStr);
                    finalizeAssistantMessage(assistantMessageId, answerText, sources, doneMeta);
                  } catch (_) {}
                }
              }
            }
          }
        } else {
          // STANDARD JSON
          const response = await fetch('/api/v1/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
            body: JSON.stringify({ query, collection_ids: [collectionId], query_transformation: strategy, rerank, compress_context: compress })
          });
          const data = await response.json();
          finalizeAssistantMessage(assistantMessageId, data.answer, data.citations, data);
        }
      } catch (err) {
        updateAssistantText(assistantMessageId, 'Error executing RAG pipeline: ' + err.message);
      }
    }

    function appendUserMessage(text) {
      const container = document.getElementById('chat-messages');
      const div = document.createElement('div');
      div.className = 'flex gap-3 text-sm max-w-3xl ml-auto justify-end';
      div.innerHTML = `
        <div class="bg-indigo-600 rounded-2xl px-4 py-3 text-white max-w-xl">
          <p class="leading-relaxed">${escapeHtml(text)}</p>
        </div>
        <div class="w-8 h-8 rounded-lg bg-indigo-500 text-white flex items-center justify-center shrink-0">
          <i class="fa-solid fa-user text-xs"></i>
        </div>
      `;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
    }

    function appendAssistantSkeleton(id) {
      const container = document.getElementById('chat-messages');
      const div = document.createElement('div');
      div.id = id;
      div.className = 'flex gap-3 text-sm max-w-3xl';
      div.innerHTML = `
        <div class="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0">
          <i class="fa-solid fa-robot"></i>
        </div>
        <div class="bg-gray-900 border border-gray-800 rounded-2xl p-4 text-gray-200 space-y-3 flex-1">
          <div class="assistant-content leading-relaxed text-xs streaming-pulse">Thinking & retrieving knowledge sources...</div>
          <div class="assistant-meta hidden"></div>
        </div>
      `;
      container.appendChild(div);
      container.scrollTop = container.scrollHeight;
      return div;
    }

    function updateAssistantText(id, text) {
      const box = document.getElementById(id);
      if (!box) return;
      const content = box.querySelector('.assistant-content');
      content.classList.remove('streaming-pulse');
      content.innerHTML = escapeHtml(text).replace(/\\[(\\d+)\\]/g, '<span class="inline-block px-1.5 py-0.2 mx-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono text-[10px] font-bold border border-indigo-500/30">[$1]</span>');
      document.getElementById('chat-messages').scrollTop = document.getElementById('chat-messages').scrollHeight;
    }

    function finalizeAssistantMessage(id, answer, citations, meta) {
      updateAssistantText(id, answer);
      const box = document.getElementById(id);
      if (!box) return;

      const metaDiv = box.querySelector('.assistant-meta');
      metaDiv.classList.remove('hidden');

      const queryId = meta.query_id || '';
      const groundedness = meta.groundedness_score !== undefined ? (meta.groundedness_score * 100).toFixed(0) : '100';
      const isHallucination = meta.hallucination_warning || false;
      const isCached = meta.cached || false;

      let citationsHtml = '';
      if (citations && citations.length > 0) {
        citationsHtml = `
          <div class="border-t border-gray-800 pt-2.5 mt-2">
            <span class="text-[10px] font-bold uppercase tracking-wider text-gray-400">Verified Citations (${citations.length})</span>
            <div class="space-y-1.5 mt-1.5">
              ${citations.map(c => `
                <div class="text-[11px] bg-gray-950/70 border border-gray-800 rounded-lg p-2 text-gray-300">
                  <div class="flex items-center justify-between text-indigo-300 font-semibold mb-1">
                    <span>[${c.source_id}] ${escapeHtml(c.section_path || 'Document')}</span>
                    <span class="text-[10px] text-gray-500">Score: ${c.relevance_score ? c.relevance_score.toFixed(2) : '1.0'}</span>
                  </div>
                  <p class="text-gray-400 italic">"${escapeHtml(c.snippet || '')}"</p>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      }

      metaDiv.innerHTML = `
        <div class="flex items-center justify-between border-t border-gray-800 pt-2 text-[10px] text-gray-400">
          <div class="flex items-center gap-2">
            <span class="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">Grounded: ${groundedness}%</span>
            ${isHallucination ? '<span class="px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">Hallucination Warning</span>' : ''}
            ${isCached ? '<span class="px-2 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20 font-medium">Cache Hit</span>' : ''}
            <span>Latency: ${meta.latency_ms || 0}ms</span>
          </div>

          <div class="flex items-center gap-1.5">
            <span class="text-gray-500">Helpful?</span>
            <button onclick="openFeedbackModal('${queryId}', true)" class="hover:text-emerald-400 px-1 py-0.5" title="Thumbs Up"><i class="fa-regular fa-thumbs-up"></i></button>
            <button onclick="openFeedbackModal('${queryId}', false)" class="hover:text-rose-400 px-1 py-0.5" title="Thumbs Down"><i class="fa-regular fa-thumbs-down"></i></button>
          </div>
        </div>
        ${citationsHtml}
      `;
    }

    // FEEDBACK HANDLING
    function openFeedbackModal(queryId, isHelpful) {
      document.getElementById('feedback-query-id').value = queryId;
      document.getElementById('feedback-is-helpful').value = isHelpful;
      document.getElementById('feedback-modal').classList.remove('hidden');
    }
    function closeFeedbackModal() { document.getElementById('feedback-modal').classList.add('hidden'); }

    async function handleSubmitFeedback(e) {
      e.preventDefault();
      const queryId = document.getElementById('feedback-query-id').value;
      const isHelpful = document.getElementById('feedback-is-helpful').value === 'true';
      const rating = parseInt(document.getElementById('feedback-rating').value);
      const category = document.getElementById('feedback-category').value;
      const comment = document.getElementById('feedback-comment').value;

      try {
        const res = await fetch('/api/v1/feedback', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${authToken}` },
          body: JSON.stringify({
            query_id: queryId,
            is_helpful: isHelpful,
            rating: rating,
            feedback_type: category,
            comment: comment || null
          })
        });
        if (!res.ok) throw new Error('Feedback submission failed');
        closeFeedbackModal();
        alert('Thank you! Your feedback has been recorded in the platform telemetry.');
        loadAnalyticsOverview();
      } catch (err) {
        alert(err.message);
      }
    }

    // DOCUMENT UPLOAD & BACKGROUND QUEUE
    document.getElementById('file-input').addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        document.getElementById('file-chosen-text').innerText = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      }
    });

    async function handleUploadDocument(e) {
      e.preventDefault();
      const fileInput = document.getElementById('file-input');
      const file = fileInput.files[0];
      if (!file || !authToken) return;

      const collectionId = document.getElementById('upload-collection-select').value;
      const isAsync = document.getElementById('upload-async-toggle').checked;

      const formData = new FormData();
      formData.append('file', file);
      formData.append('collection_id', collectionId);
      formData.append('async_mode', isAsync.toString());

      const btn = document.getElementById('upload-submit-btn');
      btn.innerText = 'Uploading...';
      btn.disabled = true;

      try {
        const res = await fetch('/api/v1/documents/upload', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${authToken}` },
          body: formData
        });
        const doc = await res.json();
        const jobId = res.headers.get('X-Job-ID');

        if (isAsync && jobId) {
          startJobPolling(jobId, file.name);
        } else {
          alert(`Document successfully indexed (${doc.status})!`);
          loadDocumentsList();
        }
      } catch (err) {
        alert('Upload failed: ' + err.message);
      } finally {
        btn.innerText = 'Ingest Document';
        btn.disabled = false;
        fileInput.value = '';
        document.getElementById('file-chosen-text').innerText = 'Click to browse or drag and drop files here';
      }
    }

    function startJobPolling(jobId, filename) {
      const activeBox = document.getElementById('active-job-box');
      const emptyBox = document.getElementById('no-active-job');
      activeBox.classList.remove('hidden');
      emptyBox.classList.add('hidden');

      document.getElementById('job-doc-name').innerText = filename;

      if (pollingInterval) clearInterval(pollingInterval);

      pollingInterval = setInterval(async () => {
        try {
          const res = await fetch(`/api/v1/documents/jobs/${jobId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
          });
          if (!res.ok) return;
          const job = await res.json();

          document.getElementById('job-status-pill').innerText = job.status;
          document.getElementById('job-stage-text').innerText = `Stage: ${job.stage}`;
          document.getElementById('job-progress-text').innerText = `${job.progress}%`;
          document.getElementById('job-progress-bar').style.width = `${job.progress}%`;

          if (job.status === 'completed' || job.status === 'failed') {
            clearInterval(pollingInterval);
            pollingInterval = null;
            if (job.status === 'completed') {
              document.getElementById('job-status-pill').className = 'px-2 py-0.5 rounded-full text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
            } else {
              document.getElementById('job-status-pill').className = 'px-2 py-0.5 rounded-full text-[10px] font-mono bg-rose-500/10 text-rose-400 border border-rose-500/20';
            }
            loadDocumentsList();
          }
        } catch (e) {
          console.error(e);
        }
      }, 1500);
    }

    async function loadDocumentsList() {
      if (!authToken) return;
      try {
        const res = await fetch('/api/v1/documents', {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const docs = await res.json();
        const tbody = document.getElementById('documents-table-body');
        if (docs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-6 text-center text-gray-500">No documents ingested yet.</td></tr>';
          return;
        }
        tbody.innerHTML = docs.map(d => `
          <tr class="hover:bg-gray-900/40">
            <td class="px-6 py-3.5 font-medium text-white flex items-center gap-2">
              <i class="fa-solid fa-file-lines text-indigo-400"></i> ${escapeHtml(d.title)}
            </td>
            <td class="px-6 py-3.5 text-gray-400 font-mono">${escapeHtml(d.mime_type)}</td>
            <td class="px-6 py-3.5 font-mono text-gray-500">${d.content_hash.substring(0, 10)}...</td>
            <td class="px-6 py-3.5">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-mono ${d.status === 'indexed' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}">${d.status}</span>
            </td>
            <td class="px-6 py-3.5 text-gray-400">${new Date(d.created_at).toLocaleDateString()}</td>
          </tr>
        `).join('');
      } catch (e) {
        console.error(e);
      }
    }

    // ANALYTICS OVERVIEW
    async function loadAnalyticsOverview() {
      if (!authToken) return;
      try {
        const res = await fetch('/api/v1/analytics/overview', {
          headers: { 'Authorization': `Bearer ${authToken}` }
        });
        const data = await res.json();

        document.getElementById('kpi-queries').innerText = data.total_queries;
        document.getElementById('kpi-cache-rate').innerText = (data.cache_hit_rate * 100).toFixed(1) + '%';
        document.getElementById('kpi-latency').innerText = data.average_latency_ms.toFixed(0) + ' ms';
        document.getElementById('kpi-cost').innerText = '$' + data.total_cost_usd.toFixed(4);
        document.getElementById('kpi-hallucination').innerText = (data.hallucination_rate * 100).toFixed(1) + '%';
        document.getElementById('kpi-satisfaction').innerText = (data.positive_feedback_rate * 100).toFixed(0) + '%';

        document.getElementById('score-groundedness').innerText = data.average_groundedness.toFixed(2);
        document.getElementById('bar-groundedness').style.width = (data.average_groundedness * 100) + '%';

        document.getElementById('score-context').innerText = data.average_context_relevance.toFixed(2);
        document.getElementById('bar-context').style.width = (data.average_context_relevance * 100) + '%';

        document.getElementById('score-answer').innerText = data.average_answer_relevance.toFixed(2);
        document.getElementById('bar-answer').style.width = (data.average_answer_relevance * 100) + '%';

        // Models Breakdown Table
        const modelsTable = document.getElementById('models-table-body');
        const models = Object.keys(data.model_breakdown);
        if (models.length === 0) {
          modelsTable.innerHTML = '<tr><td colspan="4" class="px-6 py-6 text-center text-gray-500">No query data recorded yet.</td></tr>';
        } else {
          modelsTable.innerHTML = models.map(m => `
            <tr>
              <td class="px-6 py-3 font-medium text-white">${escapeHtml(m)}</td>
              <td class="px-6 py-3 font-mono">${data.model_breakdown[m]}</td>
              <td class="px-6 py-3 font-mono text-emerald-400">$${(data.cost_by_model[m] || 0).toFixed(5)}</td>
              <td class="px-6 py-3 text-indigo-400 font-medium">${m.includes('cache') ? 'Sub-1ms O(1)' : 'Full RAG Pipeline'}</td>
            </tr>
          `).join('');
        }
      } catch (e) {
        console.error('Analytics load error', e);
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
  </script>
</body>
</html>
"""
