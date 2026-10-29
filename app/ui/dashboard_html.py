DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Notebook Simulator — Product Roadmap Q3</title>
  
  <!-- Google Fonts: Inter (400, 500, 600) -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  
  <!-- Tailwind CSS via CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  
  <!-- Iconify CDN (solar:* icons) -->
  <script src="https://code.iconify.design/iconify-icon/1.0.7/iconify-icon.min.js"></script>

  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: {
            sans: ['Inter', 'sans-serif'],
            mono: ['"JetBrains Mono"', 'monospace'],
          }
        }
      }
    }
  </script>

  <style>
    /* Custom scrollbar: 5px width, specific #e4e4e7 thumb color */
    ::-webkit-scrollbar {
      width: 5px;
      height: 5px;
    }
    ::-webkit-scrollbar-track {
      background: transparent;
    }
    ::-webkit-scrollbar-thumb {
      background: #e4e4e7;
      border-radius: 9999px;
    }
    ::-webkit-scrollbar-thumb:hover {
      background: #d4d4d8;
    }

    /* Critical fidelity constraint: contenteditable placeholder pattern */
    [contenteditable]:empty:before {
      content: attr(placeholder);
      color: #a1a1aa;
      pointer-events: none;
    }

    [contenteditable]:focus {
      outline: none;
    }

    /* Active format button visual state */
    .fmt-btn.active {
      background-color: #3f3f46;
      color: #ffffff;
    }
  </style>
</head>
<body class="bg-white text-zinc-900 h-screen flex overflow-hidden selection:bg-zinc-200/70 font-sans antialiased">

  <!-- MOBILE SIDEBAR BACKDROP OVERLAY -->
  <div id="sidebar-backdrop" onclick="toggleSidebar()" class="hidden fixed inset-0 bg-black/20 backdrop-blur-xs z-30 md:hidden transition-opacity duration-300"></div>

  <!-- SECTION 1: SIDEBAR -->
  <aside id="sidebar" class="w-64 z-40 bg-[#fbfbfc] border-r border-zinc-200 flex flex-col justify-between transition-all duration-300 md:static md:flex hidden flex-shrink-0">
    <div class="p-3 space-y-4">
      <!-- HEADER / LOGO -->
      <div class="flex items-center justify-between px-2 py-1">
        <div class="flex items-center gap-2.5">
          <div class="w-5 h-5 bg-zinc-900 rounded flex items-center justify-center text-white text-[10px] font-bold tracking-tight shadow-xs">
            NB
          </div>
          <span class="text-xs font-semibold text-zinc-800 tracking-tight">Notebook Simulator</span>
        </div>
        <button onclick="toggleSidebar()" class="md:hidden text-zinc-400 hover:text-zinc-700 p-1">
          <iconify-icon icon="solar:close-circle-linear" class="text-base"></iconify-icon>
        </button>
      </div>

      <!-- SEARCH INPUT WITH ⌘K BADGE -->
      <div class="relative px-1">
        <iconify-icon icon="solar:magnifer-linear" class="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-sm"></iconify-icon>
        <input type="text" id="sidebar-search" placeholder="Search..." class="w-full bg-zinc-100/80 border border-zinc-200/80 rounded-lg pl-8 pr-11 py-1.5 text-xs text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-zinc-300 transition">
        <kbd class="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] font-mono text-zinc-400 bg-white border border-zinc-200 px-1 py-0.5 rounded shadow-xs">⌘K</kbd>
      </div>

      <!-- NAVIGATION: FAVORITES & PRIVATE NOTES -->
      <nav class="space-y-4 px-1 text-xs">
        <!-- FAVORITES GROUP -->
        <div>
          <div class="px-2 py-1 text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Favorites</div>
          <div class="mt-1 space-y-0.5">
            <!-- ACTIVE ITEM: Product Roadmap Q3 -->
            <a href="#" class="bg-zinc-200/60 shadow-[inset_0_1px_0_rgba(255,255,255,0.4)] text-zinc-900 font-medium px-2.5 py-1.5 rounded-lg flex items-center gap-2 transition duration-300">
              <iconify-icon icon="solar:document-text-linear" class="text-zinc-700 text-sm"></iconify-icon>
              <span class="truncate">Product Roadmap Q3</span>
            </a>
            <a href="#" class="text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 px-2.5 py-1.5 rounded-lg flex items-center gap-2 transition duration-300">
              <iconify-icon icon="solar:folder-linear" class="text-zinc-400 text-sm"></iconify-icon>
              <span class="truncate">Engineering Specs</span>
            </a>
            <a href="#" class="text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 px-2.5 py-1.5 rounded-lg flex items-center gap-2 transition duration-300">
              <iconify-icon icon="solar:star-linear" class="text-zinc-400 text-sm"></iconify-icon>
              <span class="truncate">Design System v2</span>
            </a>
          </div>
        </div>

        <!-- PRIVATE NOTES GROUP -->
        <div>
          <div class="px-2 py-1 text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Private Notes</div>
          <div class="mt-1 space-y-0.5">
            <a href="#" class="text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 px-2.5 py-1.5 rounded-lg flex items-center gap-2 transition duration-300">
              <iconify-icon icon="solar:notes-linear" class="text-zinc-400 text-sm"></iconify-icon>
              <span class="truncate">Sprint Planning</span>
            </a>
            <a href="#" class="text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 px-2.5 py-1.5 rounded-lg flex items-center gap-2 transition duration-300">
              <iconify-icon icon="solar:document-text-linear" class="text-zinc-400 text-sm"></iconify-icon>
              <span class="truncate">Security & Compliance</span>
            </a>
            <a href="#" class="text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 px-2.5 py-1.5 rounded-lg flex items-center gap-2 transition duration-300">
              <iconify-icon icon="solar:code-linear" class="text-zinc-400 text-sm"></iconify-icon>
              <span class="truncate">API Reference Docs</span>
            </a>
          </div>
        </div>

        <!-- EKIP KNOWLEDGE & AI -->
        <div>
          <div class="px-2 py-1 text-[11px] font-medium text-zinc-400 uppercase tracking-wider">AI Knowledge Base</div>
          <div class="mt-1 space-y-0.5">
            <button onclick="openKnowledgeModal()" class="w-full text-left text-zinc-600 hover:bg-zinc-100/80 hover:text-zinc-900 px-2.5 py-1.5 rounded-lg flex items-center justify-between transition duration-300">
              <div class="flex items-center gap-2">
                <iconify-icon icon="solar:database-linear" class="text-zinc-400 text-sm"></iconify-icon>
                <span class="truncate">Documents & Collections</span>
              </div>
              <span id="sidebar-doc-count" class="text-[10px] bg-zinc-200/60 px-1.5 py-0.2 rounded font-mono">0</span>
            </button>
            <button onclick="toggleAIPanel()" class="w-full text-left text-indigo-700 bg-indigo-50/60 hover:bg-indigo-100/60 px-2.5 py-1.5 rounded-lg flex items-center justify-between transition duration-300 font-medium">
              <div class="flex items-center gap-2">
                <iconify-icon icon="solar:magic-stick-3-linear" class="text-indigo-600 text-sm"></iconify-icon>
                <span class="truncate">EKIP Grounded AI</span>
              </div>
              <span class="text-[9px] bg-indigo-100 text-indigo-700 px-1 rounded font-bold">RAG</span>
            </button>
          </div>
        </div>
      </nav>
    </div>

    <!-- USER FOOTER (Alex Doe with exact dicebear avatar) -->
    <div onclick="openAuthModal()" class="flex items-center justify-between p-3 border-t border-zinc-200 hover:bg-zinc-100/60 transition cursor-pointer select-none">
      <div class="flex items-center gap-2.5">
        <img src="https://api.dicebear.com/7.x/notionists/svg?seed=Alex&backgroundColor=e4e4e7" class="w-7 h-7 rounded-full border border-zinc-200" alt="Alex Doe">
        <div class="text-left">
          <div id="sidebar-user-name" class="text-xs font-semibold text-zinc-800 leading-tight">Alex Doe</div>
          <div id="sidebar-tenant-name" class="text-[10px] text-zinc-400 leading-tight">Enterprise Workspace</div>
        </div>
      </div>
      <iconify-icon icon="solar:alt-arrow-up-linear" class="text-zinc-400 text-xs"></iconify-icon>
    </div>
  </aside>

  <!-- MAIN WORKSPACE CONTAINER -->
  <main class="flex-1 flex flex-col h-full overflow-hidden bg-white relative">
    
    <!-- SECTION 2: TOPBAR -->
    <header class="h-12 sticky top-0 z-30 backdrop-blur-md bg-white/90 border-b border-zinc-200 px-4 sm:px-8 flex items-center justify-between">
      <!-- LEFT: MOBILE TOGGLE & BREADCRUMBS -->
      <div class="flex items-center gap-2">
        <button id="sidebar-toggle-btn" onclick="toggleSidebar()" class="md:hidden mr-1 text-zinc-600 hover:text-zinc-900 p-1.5 rounded-lg hover:bg-zinc-100 transition">
          <iconify-icon icon="solar:hamburger-menu-linear" class="text-base"></iconify-icon>
        </button>
        <div class="flex items-center gap-1.5 text-xs text-zinc-500 font-medium">
          <span class="hover:underline decoration-zinc-300 underline-offset-4 cursor-pointer">Workspace</span>
          <span class="text-zinc-300">/</span>
          <span class="text-zinc-900 font-semibold hover:underline decoration-zinc-300 underline-offset-4 cursor-pointer">Product Roadmap Q3</span>
        </div>
      </div>

      <!-- RIGHT: MODE TOGGLE & ACTION BUTTONS -->
      <div class="flex items-center gap-2">
        <!-- MODE TOGGLE (Edit vs View) -->
        <div class="flex items-center gap-1.5 text-xs text-zinc-500 mr-2">
          <span id="mode-label-view" class="font-medium text-zinc-400">View</span>
          <label class="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" id="mode-toggle" checked onchange="handleModeToggle(this)" class="sr-only peer">
            <div class="w-8 h-4 bg-zinc-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-zinc-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-zinc-900"></div>
          </label>
          <span id="mode-label-edit" class="font-medium text-zinc-900">Edit</span>
        </div>

        <!-- ACTION: CLOCK CIRCLE -->
        <button title="Page History" class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition duration-300 hover:scale-110">
          <iconify-icon icon="solar:clock-circle-linear" class="text-base"></iconify-icon>
        </button>

        <!-- ACTION: MENU DOTS CIRCLE -->
        <button title="More Settings" class="p-1.5 rounded-lg text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition duration-300 hover:scale-110">
          <iconify-icon icon="solar:menu-dots-circle-linear" class="text-base"></iconify-icon>
        </button>

        <!-- ACTION: ASK AI PILL -->
        <button id="topbar-ai-btn" onclick="toggleAIPanel()" class="px-3 py-1.5 rounded-lg bg-zinc-100 hover:bg-zinc-200/80 text-zinc-900 text-xs font-semibold transition duration-300 flex items-center gap-1.5 border border-zinc-200 hover:scale-105">
          <iconify-icon icon="solar:magic-stick-3-linear" class="text-indigo-600 text-sm"></iconify-icon>
          <span class="hidden sm:inline">Ask AI</span>
        </button>

        <!-- PRIMARY: SHARE BUTTON -->
        <button id="share-btn" onclick="handleShareClick()" class="ml-1 px-3.5 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-medium transition duration-300 hover:shadow-lg flex items-center gap-1.5">
          Share
        </button>
      </div>
    </header>

    <!-- SECTION 3: MAIN EDITOR CONTENT -->
    <div id="editor-viewport" class="flex-1 overflow-y-auto px-6 sm:px-16 py-10">
      <div class="max-w-3xl mx-auto space-y-6">

        <!-- TITLE WITH QUIRK MARGIN & HOVER EMOJI AT -left-12 -->
        <div class="relative group">
          <button class="absolute -left-12 top-2.5 opacity-0 group-hover:opacity-100 transition duration-300 text-zinc-400 hover:text-zinc-800 p-1.5 rounded-lg hover:bg-zinc-100 hover:scale-110" title="Change Emoji / Icon">
            <iconify-icon icon="solar:emoji-keyboard-linear" class="text-xl"></iconify-icon>
          </button>
          <h1 id="main-doc-title" contenteditable="true" placeholder="Untitled Document" class="-ml-2 p-2 text-4xl sm:text-5xl font-bold tracking-tight text-zinc-900 outline-none leading-tight rounded-lg">Product Roadmap Q3</h1>
        </div>

        <!-- METADATA ROW (contenteditable="false") -->
        <div contenteditable="false" class="flex flex-wrap items-center gap-4 text-xs text-zinc-500 py-3 border-b border-zinc-100 select-none">
          <div class="flex items-center gap-1.5">
            <iconify-icon icon="solar:calendar-linear" class="text-zinc-400 text-sm"></iconify-icon>
            <span>July 1 – September 30, 2026</span>
          </div>
          <div class="flex items-center gap-1.5">
            <img src="https://api.dicebear.com/7.x/notionists/svg?seed=Alex&backgroundColor=e4e4e7" class="w-4 h-4 rounded-full border border-zinc-200" alt="Alex">
            <span>Alex Doe</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="bg-zinc-100/80 border border-zinc-200 text-zinc-700 font-medium px-2 py-0.5 rounded text-[11px]">Planning</span>
            <span class="bg-zinc-100/80 border border-zinc-200 text-zinc-700 font-medium px-2 py-0.5 rounded text-[11px]">Q3</span>
          </div>
        </div>

        <!-- INTRO PARAGRAPH -->
        <p contenteditable="true" placeholder="Type something, or press '/' for commands..." class="text-zinc-800 text-base leading-relaxed outline-none">
          This roadmap establishes the foundational architecture for EKIP's next-generation enterprise retrieval pipeline. All key results emphasize zero-hallucination verification, sub-50ms hybrid retrieval without GPU dependencies, and strictly isolated multi-tenant workspaces.
        </p>

        <!-- SUBHEADING -->
        <h2 contenteditable="true" placeholder="Heading 2" class="text-xl font-bold text-zinc-900 mt-8 mb-2 outline-none tracking-tight">
          Milestones & Deliverables
        </h2>

        <!-- CHECKLIST ITEMS (Quirk: -ml-1.5, grab handle at -left-6, custom SVG tick M5 13l4 4L19 7) -->
        <ul class="space-y-2.5 my-4">
          <li class="group relative flex items-start gap-2.5 -ml-1.5 p-1 rounded-md hover:bg-zinc-50/60 transition duration-300">
            <span class="absolute -left-6 top-1.5 opacity-0 group-hover:opacity-100 transition duration-300 cursor-grab text-zinc-300 hover:text-zinc-600">
              <iconify-icon icon="solar:menu-dots-bold" class="text-base"></iconify-icon>
            </span>
            <label class="relative flex items-center justify-center mt-1 cursor-pointer">
              <input type="checkbox" checked onchange="toggleTaskText(this)" class="peer sr-only">
              <div class="w-4 h-4 rounded border border-zinc-300 peer-checked:bg-zinc-900 peer-checked:border-zinc-900 flex items-center justify-center transition">
                <svg class="w-3.5 h-3.5 text-white pointer-events-none stroke-current" viewBox="0 0 24 24" fill="none" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
            </label>
            <span contenteditable="true" class="task-text text-sm text-zinc-800 outline-none flex-1 line-through text-zinc-400">Implement Hybrid Dense (FastEmbed) + Lexical (PostgreSQL GIN) search with Reciprocal Rank Fusion</span>
          </li>

          <li class="group relative flex items-start gap-2.5 -ml-1.5 p-1 rounded-md hover:bg-zinc-50/60 transition duration-300">
            <span class="absolute -left-6 top-1.5 opacity-0 group-hover:opacity-100 transition duration-300 cursor-grab text-zinc-300 hover:text-zinc-600">
              <iconify-icon icon="solar:menu-dots-bold" class="text-base"></iconify-icon>
            </span>
            <label class="relative flex items-center justify-center mt-1 cursor-pointer">
              <input type="checkbox" checked onchange="toggleTaskText(this)" class="peer sr-only">
              <div class="w-4 h-4 rounded border border-zinc-300 peer-checked:bg-zinc-900 peer-checked:border-zinc-900 flex items-center justify-center transition">
                <svg class="w-3.5 h-3.5 text-white pointer-events-none stroke-current" viewBox="0 0 24 24" fill="none" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
            </label>
            <span contenteditable="true" class="task-text text-sm text-zinc-800 outline-none flex-1 line-through text-zinc-400">Two-tier Redis semantic cache with vector cosine similarity thresholding (5ms repeat queries)</span>
          </li>

          <li class="group relative flex items-start gap-2.5 -ml-1.5 p-1 rounded-md hover:bg-zinc-50/60 transition duration-300">
            <span class="absolute -left-6 top-1.5 opacity-0 group-hover:opacity-100 transition duration-300 cursor-grab text-zinc-300 hover:text-zinc-600">
              <iconify-icon icon="solar:menu-dots-bold" class="text-base"></iconify-icon>
            </span>
            <label class="relative flex items-center justify-center mt-1 cursor-pointer">
              <input type="checkbox" onchange="toggleTaskText(this)" class="peer sr-only">
              <div class="w-4 h-4 rounded border border-zinc-300 peer-checked:bg-zinc-900 peer-checked:border-zinc-900 flex items-center justify-center transition">
                <svg class="w-3.5 h-3.5 text-white pointer-events-none stroke-current" viewBox="0 0 24 24" fill="none" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
            </label>
            <span contenteditable="true" class="task-text text-sm text-zinc-800 outline-none flex-1">Stage 2 Cross-Encoder reranking and Lost-in-the-Middle context prompt assembly</span>
          </li>

          <li class="group relative flex items-start gap-2.5 -ml-1.5 p-1 rounded-md hover:bg-zinc-50/60 transition duration-300">
            <span class="absolute -left-6 top-1.5 opacity-0 group-hover:opacity-100 transition duration-300 cursor-grab text-zinc-300 hover:text-zinc-600">
              <iconify-icon icon="solar:menu-dots-bold" class="text-base"></iconify-icon>
            </span>
            <label class="relative flex items-center justify-center mt-1 cursor-pointer">
              <input type="checkbox" onchange="toggleTaskText(this)" class="peer sr-only">
              <div class="w-4 h-4 rounded border border-zinc-300 peer-checked:bg-zinc-900 peer-checked:border-zinc-900 flex items-center justify-center transition">
                <svg class="w-3.5 h-3.5 text-white pointer-events-none stroke-current" viewBox="0 0 24 24" fill="none" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 13l4 4L19 7"></path>
                </svg>
              </div>
            </label>
            <span contenteditable="true" class="task-text text-sm text-zinc-800 outline-none flex-1">Real-time sentence-level citation verification [1] with automatic out-of-domain refusal</span>
          </li>
        </ul>

        <!-- BLOCKQUOTE (Quirk: border-l-[3px] border-zinc-300, bg-zinc-50/50) -->
        <blockquote contenteditable="true" placeholder="Empty blockquote" class="border-l-[3px] border-zinc-300 bg-zinc-50/50 p-4 my-6 text-sm text-zinc-700 italic rounded-r-lg outline-none leading-relaxed">
          "Quality in knowledge retrieval is not an accident; it is the deliberate result of hybrid search, deep cross-encoder re-ranking, and strict ground truth verification."
        </blockquote>

        <!-- CODE BLOCK (TypeScript with Pink: #db2777, Blue: #2563eb, Green: #16a34a & Group-hover Copy button) -->
        <div class="relative group my-6 bg-[#fbfbfc] border border-zinc-200 rounded-xl p-4 font-mono text-sm overflow-x-auto shadow-xs">
          <div class="flex items-center justify-between text-xs text-zinc-400 pb-2 mb-2 border-b border-zinc-100 select-none">
            <div class="flex items-center gap-1.5">
              <span class="w-2.5 h-2.5 rounded-full bg-zinc-200"></span>
              <span>hybrid_retrieval.ts</span>
            </div>
            <button id="copy-code-btn" onclick="handleCopyCode()" class="flex items-center gap-1.5 px-2 py-1 rounded bg-white border border-zinc-200 text-zinc-600 hover:text-zinc-900 text-xs transition duration-300 hover:scale-110 shadow-xs">
              <iconify-icon icon="solar:copy-linear" id="copy-code-icon" class="text-sm"></iconify-icon>
              <span id="copy-code-text">Copy</span>
            </button>
          </div>
          <pre class="leading-relaxed"><code><span style="color: #db2777;">interface</span> <span style="color: #2563eb;">RetrievedChunk</span> {
  <span style="color: #2563eb;">id</span>: <span style="color: #2563eb;">string</span>;
  <span style="color: #2563eb;">score</span>: <span style="color: #2563eb;">number</span>;
  <span style="color: #2563eb;">content</span>: <span style="color: #2563eb;">string</span>;
  <span style="color: #2563eb;">isGrounded</span>: <span style="color: #2563eb;">boolean</span>;
}

<span style="color: #db2777;">export async function</span> <span style="color: #2563eb;">executeRRFHybridSearch</span>(
  <span style="color: #2563eb;">query</span>: <span style="color: #2563eb;">string</span>,
  <span style="color: #2563eb;">tenantId</span>: <span style="color: #2563eb;">string</span>
): <span style="color: #2563eb;">Promise</span>&lt;<span style="color: #2563eb;">RetrievedChunk</span>[]&gt; {
  <span style="color: #db2777;">const</span> response = <span style="color: #db2777;">await</span> fetch(<span style="color: #16a34a;">`/api/v1/query?tenant=${tenantId}`</span>, {
    <span style="color: #2563eb;">method</span>: <span style="color: #16a34a;">'POST'</span>,
    <span style="color: #2563eb;">body</span>: JSON.stringify({ query, top_k: <span style="color: #2563eb;">5</span> })
  });
  <span style="color: #db2777;">return</span> response.json();
}</code></pre>
        </div>

        <!-- ADDITIONAL EDITABLE PARAGRAPH -->
        <p contenteditable="true" placeholder="Write down next steps or notes..." class="text-zinc-800 text-sm leading-relaxed outline-none pt-2">
          Use the floating formatting toolbar below to format selected text. Click <strong>Ask AI</strong> in the top header or sidebar to query your enterprise documents and insert verified answers directly into this editor.
        </p>

      </div>
    </div>

    <!-- CRITICAL CONSTRAINT: FLOATING FORMATTING TOOLBAR ANCHORED AT bottom-8 -->
    <div id="format-toolbar" class="fixed bottom-8 left-1/2 -translate-x-1/2 z-30 bg-zinc-900 text-white rounded-2xl px-3 py-1.5 shadow-2xl flex items-center gap-1 border border-zinc-800 backdrop-blur-md transition-all duration-300">
      <button onclick="formatDoc('bold')" title="Bold (⌘B)" class="fmt-btn p-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-800 transition">
        <iconify-icon icon="solar:text-bold-linear" class="text-base"></iconify-icon>
      </button>
      <button onclick="formatDoc('italic')" title="Italic (⌘I)" class="fmt-btn p-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-800 transition">
        <iconify-icon icon="solar:text-italic-linear" class="text-base"></iconify-icon>
      </button>
      <button onclick="formatDoc('underline')" title="Underline (⌘U)" class="fmt-btn p-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-800 transition">
        <iconify-icon icon="solar:text-underline-linear" class="text-base"></iconify-icon>
      </button>
      <button onclick="formatDoc('strikeThrough')" title="Strikethrough" class="fmt-btn p-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-800 transition">
        <iconify-icon icon="solar:text-cross-linear" class="text-base"></iconify-icon>
      </button>
      <div class="h-4 w-[1px] bg-zinc-700 mx-1"></div>
      <button onclick="formatDoc('insertUnorderedList')" title="Bullet List" class="fmt-btn p-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-800 transition">
        <iconify-icon icon="solar:list-linear" class="text-base"></iconify-icon>
      </button>
      <button onclick="formatDoc('insertOrderedList')" title="Numbered List" class="fmt-btn p-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-800 transition">
        <iconify-icon icon="solar:list-1-linear" class="text-base"></iconify-icon>
      </button>
      <button onclick="insertCodeSnippet()" title="Code Block" class="fmt-btn p-1.5 rounded-lg text-zinc-300 hover:text-white hover:bg-zinc-800 transition">
        <iconify-icon icon="solar:code-linear" class="text-base"></iconify-icon>
      </button>
      <div class="h-4 w-[1px] bg-zinc-700 mx-1"></div>
      <button onclick="toggleAIPanel()" title="Ask AI at Cursor" class="px-2 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1 transition">
        <iconify-icon icon="solar:magic-stick-3-linear" class="text-xs"></iconify-icon>
        <span>AI</span>
      </button>
    </div>

  </main>

  <!-- SLIDE-OVER NOTION AI / EKIP COPILOT PANEL -->
  <div id="ai-panel" class="fixed top-0 right-0 h-full w-96 bg-white border-l border-zinc-200 z-50 shadow-2xl flex flex-col transform translate-x-full transition-transform duration-300 ease-in-out">
    <div class="p-4 border-b border-zinc-200 flex items-center justify-between bg-zinc-50/50">
      <div class="flex items-center gap-2">
        <div class="w-6 h-6 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-xs shadow-xs">
          <iconify-icon icon="solar:magic-stick-3-linear"></iconify-icon>
        </div>
        <div>
          <h3 class="text-xs font-bold text-zinc-900 leading-tight">EKIP Grounded AI Copilot</h3>
          <p class="text-[10px] text-zinc-400">Strictly verified enterprise answers</p>
        </div>
      </div>
      <button onclick="toggleAIPanel()" class="text-zinc-400 hover:text-zinc-700 p-1 rounded-md hover:bg-zinc-100 transition">
        <iconify-icon icon="solar:close-circle-linear" class="text-lg"></iconify-icon>
      </button>
    </div>

    <!-- AI CHAT HISTORY -->
    <div id="ai-messages" class="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
      <div class="p-3 rounded-xl bg-zinc-100/70 border border-zinc-200/60 text-zinc-700 space-y-1">
        <div class="font-semibold text-zinc-900 flex items-center gap-1.5">
          <iconify-icon icon="solar:shield-check-linear" class="text-emerald-600"></iconify-icon>
          Zero Hallucination Assistant
        </div>
        <p class="leading-relaxed">
          Ask questions against your uploaded documents. Responses include exact citations <span class="text-indigo-600 font-bold">[1]</span> and can be inserted straight into your document.
        </p>
      </div>
    </div>

    <!-- AI PROMPT INPUT & CONTROLS -->
    <div class="p-4 border-t border-zinc-200 bg-white space-y-2">
      <div class="flex items-center justify-between text-[11px] text-zinc-500">
        <span id="ai-status">Ready</span>
        <button onclick="openKnowledgeModal()" class="text-indigo-600 hover:underline">Manage Knowledge</button>
      </div>
      <div class="relative">
        <textarea id="ai-input" rows="2" placeholder="Ask anything about your documents..." onkeydown="handleAIKeyDown(event)" class="w-full bg-zinc-50 border border-zinc-200 rounded-xl p-2.5 text-xs text-zinc-900 placeholder:text-zinc-400 focus:outline-none focus:border-indigo-500 resize-none"></textarea>
        <button onclick="submitAIQuery()" class="absolute right-2.5 bottom-2.5 p-1.5 bg-zinc-900 hover:bg-zinc-800 text-white rounded-lg transition hover:scale-105">
          <iconify-icon icon="solar:arrow-up-linear" class="text-xs"></iconify-icon>
        </button>
      </div>
    </div>
  </div>

  <!-- KNOWLEDGE BASE & DOCUMENT UPLOAD MODAL -->
  <div id="knowledge-modal" class="hidden fixed inset-0 bg-black/30 backdrop-blur-xs z-50 flex items-center justify-center p-4">
    <div class="bg-white border border-zinc-200 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
      <div class="flex items-center justify-between border-b border-zinc-100 pb-3">
        <div class="flex items-center gap-2">
          <iconify-icon icon="solar:database-linear" class="text-zinc-700 text-lg"></iconify-icon>
          <h3 class="text-sm font-bold text-zinc-900">Enterprise Documents & Collections</h3>
        </div>
        <button onclick="closeKnowledgeModal()" class="text-zinc-400 hover:text-zinc-700">
          <iconify-icon icon="solar:close-circle-linear" class="text-lg"></iconify-icon>
        </button>
      </div>

      <!-- CREATE COLLECTION -->
      <div class="space-y-2">
        <label class="block text-xs font-semibold text-zinc-700">Create New Collection</label>
        <div class="flex gap-2">
          <input type="text" id="new-collection-name" placeholder="e.g. Q3 Roadmap Docs" class="flex-1 bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs text-zinc-900 focus:outline-none focus:border-zinc-400">
          <button onclick="createCollection()" class="px-3 py-1.5 bg-zinc-900 text-white text-xs font-medium rounded-lg hover:bg-zinc-800 transition">Create</button>
        </div>
      </div>

      <!-- UPLOAD DOCUMENT -->
      <div class="space-y-2 pt-2 border-t border-zinc-100">
        <label class="block text-xs font-semibold text-zinc-700">Upload Document (.txt, .md, .pdf)</label>
        <div class="flex gap-2">
          <select id="upload-collection-select" class="flex-1 bg-zinc-50 border border-zinc-200 rounded-lg px-3 py-1.5 text-xs text-zinc-900 focus:outline-none">
            <option value="">Select Collection</option>
          </select>
          <input type="file" id="doc-file-input" class="hidden" onchange="handleFileUpload(event)">
          <button onclick="document.getElementById('doc-file-input').click()" class="px-3 py-1.5 bg-zinc-100 border border-zinc-200 text-zinc-800 text-xs font-medium rounded-lg hover:bg-zinc-200 transition flex items-center gap-1.5">
            <iconify-icon icon="solar:upload-linear"></iconify-icon>
            <span>Upload File</span>
          </button>
        </div>
      </div>

      <!-- COLLECTIONS LIST -->
      <div class="space-y-2 pt-2 border-t border-zinc-100">
        <label class="block text-xs font-semibold text-zinc-700">Active Collections</label>
        <div id="collections-list" class="max-h-40 overflow-y-auto space-y-1.5 text-xs">
          <div class="text-zinc-400 text-[11px] italic">Loading collections...</div>
        </div>
      </div>
    </div>
  </div>

  <!-- AUTH MODAL -->
  <div id="auth-modal" class="hidden fixed inset-0 bg-black/30 backdrop-blur-xs z-50 flex items-center justify-center p-4">
    <div class="bg-white border border-zinc-200 rounded-2xl w-full max-w-sm p-6 shadow-2xl space-y-4">
      <div class="flex items-center justify-between border-b border-zinc-100 pb-3">
        <h3 class="text-sm font-bold text-zinc-900">Workspace Authentication</h3>
        <button onclick="closeAuthModal()" class="text-zinc-400 hover:text-zinc-700">
          <iconify-icon icon="solar:close-circle-linear" class="text-lg"></iconify-icon>
        </button>
      </div>

      <div class="flex border-b border-zinc-200 text-xs font-semibold">
        <button id="auth-tab-login" onclick="setAuthMode('login')" class="flex-1 py-2 text-zinc-900 border-b-2 border-zinc-900">Sign In</button>
        <button id="auth-tab-register" onclick="setAuthMode('register')" class="flex-1 py-2 text-zinc-400 hover:text-zinc-700">Register</button>
      </div>

      <form id="auth-form" onsubmit="handleAuthSubmit(event)" class="space-y-3 text-xs">
        <div id="tenant-input-container" class="hidden space-y-1">
          <label class="block text-zinc-600 font-medium">Organization / Tenant</label>
          <input type="text" id="auth-tenant" placeholder="Acme Corp" class="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-xs text-zinc-900 focus:outline-none">
        </div>
        <div class="space-y-1">
          <label class="block text-zinc-600 font-medium">Work Email</label>
          <input type="email" id="auth-email" required placeholder="alex@enterprise.com" class="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-xs text-zinc-900 focus:outline-none">
        </div>
        <div class="space-y-1">
          <label class="block text-zinc-600 font-medium">Password</label>
          <input type="password" id="auth-password" required placeholder="••••••••" class="w-full bg-zinc-50 border border-zinc-200 rounded-lg p-2 text-xs text-zinc-900 focus:outline-none">
        </div>
        <button type="submit" class="w-full py-2 bg-zinc-900 hover:bg-zinc-800 text-white font-semibold rounded-lg text-xs transition">
          Continue
        </button>
      </form>
    </div>
  </div>

  <!-- NOTIFICATION TOAST -->
  <div id="toast" class="fixed bottom-6 right-6 z-50 bg-zinc-900 text-white text-xs px-3.5 py-2 rounded-xl shadow-xl flex items-center gap-2 transform translate-y-20 opacity-0 transition-all duration-300">
    <iconify-icon icon="solar:check-circle-linear" class="text-emerald-400 text-sm"></iconify-icon>
    <span id="toast-text">Operation successful</span>
  </div>

  <!-- JAVASCRIPT LOGIC -->
  <script>
    let authToken = localStorage.getItem('ekip_token') || null;
    let authMode = 'login';
    let currentTenant = localStorage.getItem('ekip_tenant') || 'Enterprise';

    // 1. SIDEBAR TOGGLE
    function toggleSidebar() {
      const sidebar = document.getElementById('sidebar');
      const backdrop = document.getElementById('sidebar-backdrop');
      const isHidden = sidebar.classList.contains('hidden');
      
      if (isHidden) {
        sidebar.classList.remove('hidden');
        sidebar.classList.add('absolute', 'h-full', 'shadow-2xl');
        backdrop.classList.remove('hidden');
      } else {
        sidebar.classList.add('hidden');
        sidebar.classList.remove('absolute', 'h-full', 'shadow-2xl');
        backdrop.classList.add('hidden');
      }
    }

    // 2. MODE TOGGLE (Edit vs View)
    function handleModeToggle(checkbox) {
      const isEdit = checkbox.checked;
      const editables = document.querySelectorAll('[contenteditable]');
      editables.forEach(el => {
        el.setAttribute('contenteditable', isEdit ? 'true' : 'false');
      });

      const labelEdit = document.getElementById('mode-label-edit');
      const labelView = document.getElementById('mode-label-view');
      const toolbar = document.getElementById('format-toolbar');

      if (isEdit) {
        labelEdit.className = 'font-medium text-zinc-900';
        labelView.className = 'font-medium text-zinc-400';
        toolbar.style.opacity = '1';
        toolbar.style.pointerEvents = 'auto';
      } else {
        labelEdit.className = 'font-medium text-zinc-400';
        labelView.className = 'font-medium text-zinc-900';
        toolbar.style.opacity = '0';
        toolbar.style.pointerEvents = 'none';
      }
    }

    // 3. CHECKLIST LOGIC
    function toggleTaskText(checkbox) {
      const taskText = checkbox.closest('li').querySelector('.task-text');
      if (checkbox.checked) {
        taskText.classList.add('line-through', 'text-zinc-400');
      } else {
        taskText.classList.remove('line-through', 'text-zinc-400');
      }
    }

    // 4. COPY CODE LOGIC (Change icon to check-circle and text to green for 2s)
    function handleCopyCode() {
      const codeElement = document.querySelector('pre code');
      if (!codeElement) return;
      navigator.clipboard.writeText(codeElement.innerText).then(() => {
        const btn = document.getElementById('copy-code-btn');
        const icon = document.getElementById('copy-code-icon');
        const text = document.getElementById('copy-code-text');

        icon.setAttribute('icon', 'solar:check-circle-linear');
        btn.classList.add('text-emerald-600', 'border-emerald-300');
        text.innerText = 'Copied';

        setTimeout(() => {
          icon.setAttribute('icon', 'solar:copy-linear');
          btn.classList.remove('text-emerald-600', 'border-emerald-300');
          text.innerText = 'Copy';
        }, 2000);
      });
    }

    // 5. SHARE LOGIC (Change text to "Shared" with green glow shadow-[0_0_20px_rgba(22,163,74,0.4)] for 2s)
    function handleShareClick() {
      const btn = document.getElementById('share-btn');
      const originalText = btn.innerHTML;
      btn.innerText = 'Shared';
      btn.classList.add('shadow-[0_0_20px_rgba(22,163,74,0.4)]', 'bg-emerald-600');
      btn.classList.remove('bg-zinc-900');

      setTimeout(() => {
        btn.innerHTML = originalText;
        btn.classList.remove('shadow-[0_0_20px_rgba(22,163,74,0.4)]', 'bg-emerald-600');
        btn.classList.add('bg-zinc-900');
      }, 2000);
    }

    // 6. FORMATTING LOGIC
    function formatDoc(command, value = null) {
      document.execCommand(command, false, value);
    }

    function insertCodeSnippet() {
      const selection = window.getSelection();
      if (!selection.rangeCount) return;
      const range = selection.getRangeAt(0);
      const codeNode = document.createElement('code');
      codeNode.className = 'bg-zinc-100 text-zinc-900 font-mono text-xs px-1.5 py-0.5 rounded border border-zinc-200';
      codeNode.innerText = selection.toString() || 'code';
      range.deleteContents();
      range.insertNode(codeNode);
    }

    // 7. TOAST NOTIFICATIONS
    function showToast(msg) {
      const toast = document.getElementById('toast');
      const text = document.getElementById('toast-text');
      text.innerText = msg;
      toast.classList.remove('translate-y-20', 'opacity-0');
      setTimeout(() => {
        toast.classList.add('translate-y-20', 'opacity-0');
      }, 2500);
    }

    // 8. AI COPILOT SLIDE-OVER
    function toggleAIPanel() {
      const panel = document.getElementById('ai-panel');
      const isClosed = panel.classList.contains('translate-x-full');
      if (isClosed) {
        panel.classList.remove('translate-x-full');
        document.getElementById('ai-input').focus();
      } else {
        panel.classList.add('translate-x-full');
      }
    }

    function handleAIKeyDown(e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitAIQuery();
      }
    }

    async function submitAIQuery() {
      const input = document.getElementById('ai-input');
      const query = input.value.trim();
      if (!query) return;

      input.value = '';
      const messagesContainer = document.getElementById('ai-messages');

      // User Message
      const userBubble = document.createElement('div');
      userBubble.className = 'p-2.5 rounded-xl bg-zinc-900 text-white ml-6 text-xs';
      userBubble.innerText = query;
      messagesContainer.appendChild(userBubble);

      // AI Response Bubble
      const aiBubble = document.createElement('div');
      aiBubble.className = 'p-3 rounded-xl bg-zinc-100 border border-zinc-200 text-zinc-800 mr-4 text-xs space-y-2';
      aiBubble.innerHTML = '<div class="flex items-center gap-1.5 text-zinc-400"><iconify-icon icon="solar:refresh-linear" class="animate-spin"></iconify-icon><span>Retrieving & verifying citations...</span></div>';
      messagesContainer.appendChild(aiBubble);
      messagesContainer.scrollTop = messagesContainer.scrollHeight;

      document.getElementById('ai-status').innerText = 'Generating...';

      try {
        const headers = { 'Content-Type': 'application/json' };
        if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

        const res = await fetch('/api/v1/query', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ query: query, top_k: 5 })
        });

        if (res.status === 401) {
          aiBubble.innerHTML = '<div class="text-rose-600">Please sign in to access enterprise documents. <button onclick="openAuthModal()" class="underline font-bold">Sign In</button></div>';
          document.getElementById('ai-status').innerText = 'Auth required';
          return;
        }

        const data = await res.json();
        const answerText = data.answer || 'No answer generated.';
        window.lastAnswerText = answerText;
        const groundedPct = data.metrics ? Math.round((data.metrics.groundedness || 1) * 100) : 100;
        const latency = data.metrics ? data.metrics.latency_ms : '45';
        const cacheHit = data.cache_hit ? '<span class="text-emerald-700 bg-emerald-100 px-1 py-0.5 rounded font-mono font-bold text-[10px]">Cache Hit</span>' : '';

        aiBubble.innerHTML = `
          <div class="leading-relaxed font-normal">${answerText}</div>
          <div class="pt-2 border-t border-zinc-200/70 flex items-center justify-between text-[10px] text-zinc-400">
            <div class="flex items-center gap-1.5">
              <span class="text-emerald-600 font-semibold">Grounded: ${groundedPct}%</span>
              <span>•</span>
              <span>${latency}ms</span>
              ${cacheHit}
            </div>
            <button onclick="insertLatestAIText()" class="text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1 hover:underline">
              <iconify-icon icon="solar:add-circle-linear"></iconify-icon> Insert
            </button>
          </div>
        `;
        document.getElementById('ai-status').innerText = 'Ready';
      } catch (err) {
        aiBubble.innerHTML = `<div class="text-rose-600">Error: ${err.message}</div>`;
        document.getElementById('ai-status').innerText = 'Error';
      }
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function insertLatestAIText() {
      if (window.lastAnswerText) {
        insertAITextToDoc(window.lastAnswerText);
      }
    }

    function insertAITextToDoc(text) {
      const docViewport = document.getElementById('editor-viewport');
      const p = document.createElement('p');
      p.setAttribute('contenteditable', 'true');
      p.className = 'text-zinc-800 text-sm leading-relaxed outline-none my-3 p-2 bg-indigo-50/40 border-l-2 border-indigo-500 rounded-r';
      p.innerText = text;
      docViewport.querySelector('.max-w-3xl').appendChild(p);
      showToast('Inserted AI answer into editor');
      toggleAIPanel();
    }

    // 9. KNOWLEDGE BASE & UPLOAD
    function openKnowledgeModal() {
      document.getElementById('knowledge-modal').classList.remove('hidden');
      loadCollections();
    }
    function closeKnowledgeModal() {
      document.getElementById('knowledge-modal').classList.add('hidden');
    }

    async function loadCollections() {
      const listEl = document.getElementById('collections-list');
      const selectEl = document.getElementById('upload-collection-select');
      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};

      try {
        const res = await fetch('/api/v1/collections', { headers });
        if (res.status === 401) {
          listEl.innerHTML = '<div class="text-zinc-400 italic">Sign in to view collections.</div>';
          return;
        }
        const collections = await res.json();
        listEl.innerHTML = '';
        selectEl.innerHTML = '<option value="">Select Collection</option>';

        if (!Array.isArray(collections) || collections.length === 0) {
          listEl.innerHTML = '<div class="text-zinc-400 italic">No collections found. Create one above!</div>';
          return;
        }

        document.getElementById('sidebar-doc-count').innerText = collections.length;

        collections.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.innerText = c.name;
          selectEl.appendChild(opt);

          const item = document.createElement('div');
          item.className = 'flex items-center justify-between p-2 rounded-lg bg-zinc-50 border border-zinc-200';
          item.innerHTML = `
            <div class="font-medium text-zinc-800 flex items-center gap-1.5">
              <iconify-icon icon="solar:folder-linear" class="text-zinc-500"></iconify-icon>
              <span>${c.name}</span>
            </div>
            <span class="text-[10px] text-zinc-400 font-mono">${c.id.substring(0, 8)}...</span>
          `;
          listEl.appendChild(item);
        });
      } catch (e) {
        listEl.innerHTML = `<div class="text-rose-500 text-xs">Failed to load: ${e.message}</div>`;
      }
    }

    async function createCollection() {
      const input = document.getElementById('new-collection-name');
      const name = input.value.trim();
      if (!name) return;
      const headers = { 'Content-Type': 'application/json' };
      if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

      try {
        const res = await fetch('/api/v1/collections', {
          method: 'POST',
          headers,
          body: JSON.stringify({ name, description: 'Notebook collection' })
        });
        if (res.ok) {
          input.value = '';
          showToast(`Collection "${name}" created`);
          loadCollections();
        } else {
          showToast('Failed to create collection');
        }
      } catch (err) {
        showToast(err.message);
      }
    }

    async function handleFileUpload(event) {
      const file = event.target.files[0];
      const collectionId = document.getElementById('upload-collection-select').value;
      if (!file || !collectionId) {
        alert('Please choose both a file and a collection');
        return;
      }

      const formData = new FormData();
      formData.append('file', file);
      formData.append('collection_id', collectionId);

      const headers = authToken ? { 'Authorization': `Bearer ${authToken}` } : {};

      showToast(`Uploading ${file.name}...`);
      try {
        const res = await fetch('/api/v1/documents/upload', {
          method: 'POST',
          headers,
          body: formData
        });
        if (res.ok) {
          showToast(`Uploaded ${file.name} successfully! FastEmbed indexing started.`);
          closeKnowledgeModal();
        } else {
          showToast('Upload failed');
        }
      } catch (err) {
        showToast(`Upload error: ${err.message}`);
      }
    }

    // 10. AUTHENTICATION MODAL
    function openAuthModal() {
      document.getElementById('auth-modal').classList.remove('hidden');
    }
    function closeAuthModal() {
      document.getElementById('auth-modal').classList.add('hidden');
    }
    function setAuthMode(mode) {
      authMode = mode;
      const tenantContainer = document.getElementById('tenant-input-container');
      const tabLogin = document.getElementById('auth-tab-login');
      const tabRegister = document.getElementById('auth-tab-register');

      if (mode === 'register') {
        tenantContainer.classList.remove('hidden');
        tabRegister.className = 'flex-1 py-2 text-zinc-900 border-b-2 border-zinc-900';
        tabLogin.className = 'flex-1 py-2 text-zinc-400 hover:text-zinc-700';
      } else {
        tenantContainer.classList.add('hidden');
        tabLogin.className = 'flex-1 py-2 text-zinc-900 border-b-2 border-zinc-900';
        tabRegister.className = 'flex-1 py-2 text-zinc-400 hover:text-zinc-700';
      }
    }

    async function handleAuthSubmit(e) {
      e.preventDefault();
      const email = document.getElementById('auth-email').value;
      const password = document.getElementById('auth-password').value;
      const tenant = document.getElementById('auth-tenant').value || 'Enterprise';

      try {
        if (authMode === 'register') {
          await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, role: 'admin', tenant_name: tenant })
          });
        }

        const loginRes = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        if (!loginRes.ok) throw new Error('Invalid email or password');
        const data = await loginRes.json();

        authToken = data.access_token;
        localStorage.setItem('ekip_token', authToken);
        localStorage.setItem('ekip_tenant', tenant);

        document.getElementById('sidebar-user-name').innerText = email.split('@')[0];
        document.getElementById('sidebar-tenant-name').innerText = tenant;

        showToast('Signed in successfully');
        closeAuthModal();
        loadCollections();
      } catch (err) {
        alert(err.message);
      }
    }

    // Auto-load collections on start
    window.addEventListener('DOMContentLoaded', () => {
      loadCollections();
    });
  </script>
</body>
</html>
"""
