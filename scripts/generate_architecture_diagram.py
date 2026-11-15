"""Generate high-resolution PNG architecture diagram for Hirthick's Vision Studio Backend."""

import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PNG = ROOT / "docs" / "architecture-backend.png"
REPORTS_PNG = ROOT / "reports" / "architecture-backend.png"
OUTPUT_PNG.parent.mkdir(exist_ok=True)
REPORTS_PNG.parent.mkdir(exist_ok=True)

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/lucide@latest"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;600;700&display=swap');
  * { box-sizing: border-box; }
  body {
    font-family: 'Plus Jakarta Sans', sans-serif;
    background-color: #06090e;
    color: #e2e8f0;
    margin: 0;
    padding: 40px;
    width: 1800px;
  }
  .mono { font-family: 'JetBrains Mono', monospace; }
  .card-bg { background-color: #0b111a; }
  .border-subtle { border: 1px solid #1c2636; }
  .border-accent { border: 1px solid #25D366; }
  .glow-green { box-shadow: 0 0 20px rgba(37, 211, 102, 0.15); }
  .glow-blue { box-shadow: 0 0 20px rgba(56, 189, 248, 0.15); }
  .glow-purple { box-shadow: 0 0 20px rgba(168, 85, 247, 0.15); }
</style>
</head>
<body class="p-8">

  <!-- Header Banner -->
  <div class="flex items-center justify-between pb-6 border-b border-[#1c2636] mb-8">
    <div class="flex items-center gap-4">
      <div class="w-14 h-14 rounded-2xl bg-gradient-to-tr from-[#25D366] to-[#128C7E] flex items-center justify-center shadow-lg shadow-[#25D366]/25">
        <i data-lucide="cpu" class="w-8 h-8 text-white"></i>
      </div>
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-3xl font-extrabold tracking-tight text-white">Hirthick's Vision Studio</h1>
          <span class="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-[#25D366]/15 text-[#25D366] border border-[#25D366]/40">Backend Architecture</span>
          <span class="px-3 py-1 rounded-full text-xs font-mono font-semibold bg-slate-800/80 text-slate-300 border border-slate-700">v0.9.13 Production</span>
        </div>
        <p class="text-sm text-slate-400 mt-1">Enterprise Graph-Orchestrated YouTube Shorts Video Automation Backend & MCP Co-Pilot</p>
      </div>
    </div>
    
    <div class="flex items-center gap-3">
      <div class="px-4 py-2.5 rounded-xl card-bg border-subtle flex items-center gap-2.5 text-xs">
        <span class="w-2.5 h-2.5 rounded-full bg-[#25D366] shadow-[0_0_8px_#25D366]"></span>
        <span class="text-slate-300 font-medium">ChatCut MCP: <strong class="text-white">80 Live Tools</strong></span>
      </div>
      <div class="px-4 py-2.5 rounded-xl card-bg border-subtle flex items-center gap-2.5 text-xs">
        <i data-lucide="shield-check" class="w-4 h-4 text-[#25D366]"></i>
        <span class="text-slate-300">Guardrail: <strong class="text-white">Strict Anti-SVG</strong></span>
      </div>
      <div class="px-4 py-2.5 rounded-xl card-bg border-subtle flex items-center gap-2.5 text-xs">
        <i data-lucide="check-circle-2" class="w-4 h-4 text-sky-400"></i>
        <span class="text-slate-300">Test Suite: <strong class="text-white">79/79 Passed</strong></span>
      </div>
    </div>
  </div>

  <!-- Main Architecture Grid -->
  <div class="space-y-6">

    <!-- LAYER 1: Presentation & Orchestration Gateways -->
    <div class="grid grid-cols-12 gap-5">
      <!-- Human Operator / Gatekeeper -->
      <div class="col-span-4 card-bg border-subtle rounded-2xl p-5 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-bl-full pointer-events-none"></div>
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-lg bg-amber-500/10 text-amber-400">
              <i data-lucide="user-check" class="w-5 h-5"></i>
            </div>
            <div>
              <h2 class="text-base font-bold text-white">Human Gatekeeper Layer</h2>
              <span class="text-[11px] mono text-slate-400">app/approvals/approval_service.py</span>
            </div>
          </div>
          <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30">HITL Gate</span>
        </div>
        <p class="text-xs text-slate-300 mb-3 leading-relaxed">
          Enforces explicit human creative authority before timeline writes. Pauses execution via LangGraph <span class="mono text-amber-400">interrupt()</span>.
        </p>
        <div class="space-y-1.5 text-xs mono">
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-slate-400">G1 Project Context</span>
            <span class="text-[#25D366]">Approved</span>
          </div>
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-slate-400">G2 Script & Claims</span>
            <span class="text-[#25D366]">Calibrated 130 WPM</span>
          </div>
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-slate-400">G3 Rough-Cut Cutlist</span>
            <span class="text-amber-400">Pause for Review</span>
          </div>
        </div>
      </div>

      <!-- FastAPI Web Application -->
      <div class="col-span-4 card-bg border-subtle rounded-2xl p-5 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-sky-500/5 rounded-bl-full pointer-events-none"></div>
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-lg bg-sky-500/10 text-sky-400">
              <i data-lucide="globe" class="w-5 h-5"></i>
            </div>
            <div>
              <h2 class="text-base font-bold text-white">Studio Web API & UI</h2>
              <span class="text-[11px] mono text-slate-400">app/web/server.py (Port 8000)</span>
            </div>
          </div>
          <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-sky-500/15 text-sky-300 border border-sky-500/30">FastAPI 0.141</span>
        </div>
        <p class="text-xs text-slate-300 mb-3 leading-relaxed">
          Provides end-to-end REST API endpoints, real-time pipeline progress streaming, vertical video playback, and report readers.
        </p>
        <div class="space-y-1.5 text-xs mono">
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-sky-300">POST /api/pipeline/run</span>
            <span class="text-slate-400">Async Runner</span>
          </div>
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-sky-300">GET /media/video</span>
            <span class="text-slate-400">HTTP 206 Partial</span>
          </div>
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-sky-300">GET /api/status</span>
            <span class="text-slate-400">ChatCut Telemetry</span>
          </div>
        </div>
      </div>

      <!-- State Persistence & SQLite Checkpointing -->
      <div class="col-span-4 card-bg border-subtle rounded-2xl p-5 relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 rounded-bl-full pointer-events-none"></div>
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-lg bg-purple-500/10 text-purple-400">
              <i data-lucide="database" class="w-5 h-5"></i>
            </div>
            <div>
              <h2 class="text-base font-bold text-white">Durable State & SQLite</h2>
              <span class="text-[11px] mono text-slate-400">app/persistence/ & SqliteSaver</span>
            </div>
          </div>
          <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30">WAL Mode ACID</span>
        </div>
        <p class="text-xs text-slate-300 mb-3 leading-relaxed">
          Guarantees crash-resilient recovery, immutable audit logs, deterministic reducers, and transaction lease locks.
        </p>
        <div class="space-y-1.5 text-xs mono">
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-slate-400">JobRepository</span>
            <span class="text-purple-300">studio_persistence.db</span>
          </div>
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-slate-400">LangGraph Checkpointer</span>
            <span class="text-purple-300">SqliteSaver Threads</span>
          </div>
          <div class="p-2 rounded-lg bg-[#070b12] border border-[#17202e] flex items-center justify-between">
            <span class="text-slate-400">EditorLockManager</span>
            <span class="text-purple-300">SQLite Lease Locks</span>
          </div>
        </div>
      </div>
    </div>

    <!-- LAYER 2: LangGraph Workflow Orchestration Graph -->
    <div class="card-bg border-subtle rounded-2xl p-6 relative">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-[#25D366]/10 text-[#25D366]">
            <i data-lucide="git-fork" class="w-5 h-5"></i>
          </div>
          <div>
            <h2 class="text-base font-bold text-white">LangGraph Production StateGraph Topology</h2>
            <span class="text-xs mono text-slate-400">app/orchestration/graph.py & app/orchestration/nodes.py</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 mono">Non-Linear Graph</span>
          <span class="text-xs px-2.5 py-1 rounded bg-[#25D366]/15 text-[#25D366] font-semibold mono">Deterministic Reducers</span>
        </div>
      </div>

      <!-- Graph Flow Nodes -->
      <div class="grid grid-cols-7 gap-3 text-center text-xs">
        <!-- Node 1 -->
        <div class="p-3.5 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="mono text-[11px] text-emerald-400 font-bold">1. START</div>
          <div class="p-2 rounded bg-slate-900 border border-slate-800 font-semibold text-white">load_project_node</div>
          <div class="text-[10px] text-slate-400 leading-tight">Initialize context, verify root path</div>
        </div>

        <!-- Node 2 (Parallel Fan-out) -->
        <div class="p-3.5 rounded-xl bg-[#080d14] border border-blue-900/40 space-y-2">
          <div class="mono text-[11px] text-blue-400 font-bold">2. FAN-OUT (PARALLEL)</div>
          <div class="p-1.5 rounded bg-blue-950/40 border border-blue-800/40 text-[11px] text-blue-200">validate_metadata</div>
          <div class="p-1.5 rounded bg-blue-950/40 border border-blue-800/40 text-[11px] text-blue-200">validate_asset_registry</div>
          <div class="text-[10px] text-slate-400 leading-tight">Concurrent branch execution</div>
        </div>

        <!-- Node 3 -->
        <div class="p-3.5 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="mono text-[11px] text-purple-400 font-bold">3. FAN-IN MERGE</div>
          <div class="p-2 rounded bg-slate-900 border border-slate-800 font-semibold text-white">merge_validation</div>
          <div class="text-[10px] text-slate-400 leading-tight">State reducers merge assets & dedupe</div>
        </div>

        <!-- Node 4 -->
        <div class="p-3.5 rounded-xl bg-[#080d14] border border-amber-900/40 space-y-2">
          <div class="mono text-[11px] text-amber-400 font-bold">4. INTERRUPT GATE</div>
          <div class="p-2 rounded bg-amber-950/40 border border-amber-800/40 font-semibold text-amber-200">human_approval_gate</div>
          <div class="text-[10px] text-slate-400 leading-tight">Pauses for human decision token</div>
        </div>

        <!-- Node 5 -->
        <div class="p-3.5 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="mono text-[11px] text-sky-400 font-bold">5. CONDITIONAL ROUTE</div>
          <div class="p-2 rounded bg-slate-900 border border-slate-800 font-semibold text-white">resume_workflow</div>
          <div class="text-[10px] text-slate-400 leading-tight">route_after_approval router</div>
        </div>

        <!-- Node 6 -->
        <div class="p-3.5 rounded-xl bg-[#080d14] border border-red-900/40 space-y-2">
          <div class="mono text-[11px] text-red-400 font-bold">ERROR HANDLER</div>
          <div class="p-2 rounded bg-red-950/40 border border-red-800/40 font-semibold text-red-200">handle_rejection</div>
          <div class="text-[10px] text-slate-400 leading-tight">Audit logging & safe quarantine</div>
        </div>

        <!-- Node 7 -->
        <div class="p-3.5 rounded-xl bg-[#080d14] border border-[#25D366]/40 space-y-2">
          <div class="mono text-[11px] text-[#25D366] font-bold">6. COMPLETION</div>
          <div class="p-2 rounded bg-emerald-950/40 border border-[#25D366]/50 font-semibold text-[#25D366]">complete_job_node</div>
          <div class="text-[10px] text-slate-400 leading-tight">Output certified deliverables & END</div>
        </div>
      </div>
    </div>

    <!-- LAYER 3: Deterministic Core Services (10-Phase Pipeline) -->
    <div class="card-bg border-subtle rounded-2xl p-6">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="p-2 rounded-lg bg-sky-500/10 text-sky-400">
            <i data-lucide="boxes" class="w-5 h-5"></i>
          </div>
          <div>
            <h2 class="text-base font-bold text-white">Deterministic Core Services Layer</h2>
            <span class="text-xs mono text-slate-400">app/services/ — 100% Deterministic Python Logic (Zero Black-Box Logic)</span>
          </div>
        </div>
        <span class="text-xs mono px-2.5 py-1 rounded bg-slate-800 text-slate-300">Phase 3 to Phase 10 Services</span>
      </div>

      <div class="grid grid-cols-4 gap-4">
        <!-- Service 1: ProjectScanner & Guardrail -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-emerald-400">Phase 3: Intake & Scanner</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300">Read-Only</span>
          </div>
          <div class="font-semibold text-sm text-white">ProjectScannerService</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Zero-mutation scanner. Reads candidate files, computes chunked SHA-256 hashes, generates manifest records.
          </p>
          <div class="pt-1 text-[11px] mono text-red-400 flex items-center gap-1.5">
            <i data-lucide="shield-alert" class="w-3.5 h-3.5"></i>
            <span>AssetGuardrail: Quarantines SVGs</span>
          </div>
        </div>

        <!-- Service 2: Script & Shot Planning -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-sky-400">Phase 4: Story Architecture</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-sky-500/10 text-sky-300">4 Beats</span>
          </div>
          <div class="font-semibold text-sm text-white">ScriptService & ShotPlanner</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            4-beat narrative curve (Hook, Problem, Solution, CTA) at 130 WPM. Frames Continuity: half-open intervals <span class="mono text-sky-300">[start, end)</span>.
          </p>
          <div class="pt-1 text-[11px] mono text-slate-400">
            Claims verification via ResearchService
          </div>
        </div>

        <!-- Service 3: Media Understanding -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-purple-400">Phase 5: Intelligence</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300">ffprobe</span>
          </div>
          <div class="font-semibold text-sm text-white">MediaUnderstandingService</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Extracts audio/video streams, sample rate, resolution. Generates word-level timestamps & matches candidate footage to shots.
          </p>
          <div class="pt-1 text-[11px] mono text-slate-400">
            Auto-detects ChatCut bundled ffprobe
          </div>
        </div>

        <!-- Service 4: Edit Planning -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-amber-400">Phase 6: Multi-Track</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-300">5 Tracks</span>
          </div>
          <div class="font-semibold text-sm text-white">EditPlannerService</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Translates matched clips and transcripts into a 5-track layout (V1, V2, A1, A2, TXT) and 15 atomic edit operations.
          </p>
          <div class="pt-1 text-[11px] mono text-slate-400">
            Produces immutable CutList for MCP
          </div>
        </div>

        <!-- Service 5: Assembly & Verification -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-[#25D366]">Phase 7: Timeline Assembly</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300">Transactional</span>
          </div>
          <div class="font-semibold text-sm text-white">AssemblyService</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Applies atomic operations to ChatCut timeline. Reads back state, compares layout hash, reconciles frame drift.
          </p>
          <div class="pt-1 text-[11px] mono text-slate-400">
            Generates state-diff audit deliverable
          </div>
        </div>

        <!-- Service 6: Critique Engine -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-pink-400">Phase 8: Quality Loop</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-pink-500/10 text-pink-300">7 Dimensions</span>
          </div>
          <div class="font-semibold text-sm text-white">CritiqueService</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Evaluates 7 independent dimensions: Continuity, Pacing, Readability, Audio, Claims, Brand, Technical. Pass >= 9.0/10.
          </p>
          <div class="pt-1 text-[11px] mono text-[#25D366]">
            Short #13 Score: 9.81 / 10.0 (PASS)
          </div>
        </div>

        <!-- Service 7: Publishing & Export -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-indigo-400">Phase 9: Staging</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300">Packaging</span>
          </div>
          <div class="font-semibold text-sm text-white">Export & PublishingService</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Generates 3 YouTube title variants, timestamps, description, tags, pinned comment, and verifies MP4 container integrity.
          </p>
          <div class="pt-1 text-[11px] mono text-slate-400">
            SHA-256 hash certified export
          </div>
        </div>

        <!-- Service 8: Retrospective -->
        <div class="p-4 rounded-xl bg-[#080d14] border border-[#1e2a3b] space-y-2">
          <div class="flex items-center justify-between">
            <span class="mono text-xs font-bold text-teal-400">Phase 10: Retrospective</span>
            <span class="text-[10px] mono px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-300">Governance</span>
          </div>
          <div class="font-semibold text-sm text-white">RetrospectiveService</div>
          <p class="text-xs text-slate-400 leading-relaxed">
            Compiles production KPIs, cost analysis, test pass rates, and scaling policies for expanding from Short #13 to #14+.
          </p>
          <div class="pt-1 text-[11px] mono text-slate-400">
            Automated Markdown audit report
          </div>
        </div>
      </div>
    </div>

    <!-- LAYER 4: Dynamic Animation Engine & ChatCut MCP Integration (Bottom Row) -->
    <div class="grid grid-cols-12 gap-5">

      <!-- Dynamic Animation Engine -->
      <div class="col-span-6 card-bg border-subtle rounded-2xl p-5 relative overflow-hidden">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-lg bg-orange-500/10 text-orange-400">
              <i data-lucide="layers" class="w-5 h-5"></i>
            </div>
            <div>
              <h2 class="text-base font-bold text-white">Animation & Composition Engine</h2>
              <span class="text-[11px] mono text-slate-400">app/services/render_engine.py (Pillow + FFmpeg)</span>
            </div>
          </div>
          <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-orange-500/15 text-orange-300 border border-orange-500/30">1080x1920 @ 30 FPS</span>
        </div>
        <p class="text-xs text-slate-300 mb-3 leading-relaxed">
          High-engagement typography pipeline producing vertical video with zero synthetic diffusion imagery:
        </p>
        <div class="grid grid-cols-2 gap-2 text-xs mono">
          <div class="p-2.5 rounded-lg bg-[#070b12] border border-[#17202e] space-y-1">
            <span class="text-orange-300 font-bold">Pillow Frame Generator</span>
            <div class="text-[11px] text-slate-400">900 transparent RGBA frames</div>
            <div class="text-[11px] text-slate-400">Inter font word reveals (slide-up 20px)</div>
            <div class="text-[11px] text-slate-400">Spring physics glassmorphic badges</div>
            <div class="text-[11px] text-slate-400">4px glowing progress bar</div>
          </div>
          <div class="p-2.5 rounded-lg bg-[#070b12] border border-[#17202e] space-y-1">
            <span class="text-orange-300 font-bold">FFmpeg Compositor</span>
            <div class="text-[11px] text-slate-400">Authentic UI demo scaled & cropped</div>
            <div class="text-[11px] text-slate-400">0–5s spreadsheet B-roll with 0.5s fade</div>
            <div class="text-[11px] text-slate-400">Slow Ken Burns zoom (1.0x → 1.03x)</div>
            <div class="text-[11px] text-slate-400">Audio ducking: BGM -18dB under speech</div>
          </div>
        </div>
      </div>

      <!-- ChatCut MCP Integration Layer -->
      <div class="col-span-6 card-bg border-subtle rounded-2xl p-5 relative overflow-hidden">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2.5">
            <div class="p-2 rounded-lg bg-[#25D366]/10 text-[#25D366]">
              <i data-lucide="terminal" class="w-5 h-5"></i>
            </div>
            <div>
              <h2 class="text-base font-bold text-white">ChatCut MCP Co-Pilot Layer</h2>
              <span class="text-[11px] mono text-slate-400">app/integrations/chatcut/ (Model Context Protocol)</span>
            </div>
          </div>
          <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-[#25D366]/15 text-[#25D366] border border-[#25D366]/30">6-Step Transactional</span>
        </div>
        <p class="text-xs text-slate-300 mb-3 leading-relaxed">
          Bi-directional bridge to ChatCut Desktop v0.9.13 via stdio IPC / CLI transport with complete rollback protection:
        </p>
        <div class="grid grid-cols-2 gap-2 text-xs mono">
          <div class="p-2.5 rounded-lg bg-[#070b12] border border-[#17202e] space-y-1">
            <span class="text-[#25D366] font-bold">ChatCutMCPAdapter</span>
            <div class="text-[11px] text-slate-400">Live @chatcut/cli stdio transport</div>
            <div class="text-[11px] text-slate-400">Direct pipe: \\.\pipe\chatcut-mcp-...</div>
            <div class="text-[11px] text-slate-400">80 active tools: create, edit_item, etc.</div>
            <div class="text-[11px] text-slate-400">Deterministic simulated fallback</div>
          </div>
          <div class="p-2.5 rounded-lg bg-[#070b12] border border-[#17202e] space-y-1">
            <span class="text-[#25D366] font-bold">EditorController & Lock</span>
            <div class="text-[11px] text-slate-400">1. Exclusive SQLite lease lock</div>
            <div class="text-[11px] text-slate-400">2. Pre-edit revision layout SHA-256</div>
            <div class="text-[11px] text-slate-400">3. Rollback clone: duplicate_project</div>
            <div class="text-[11px] text-slate-400">4. Idempotent batch write & drift check</div>
          </div>
        </div>
      </div>

    </div>

  </div>

  <!-- Footer Meta -->
  <div class="mt-8 pt-4 border-t border-[#1c2636] flex items-center justify-between text-xs text-slate-500 mono">
    <div>Hirthick’s Vision Studio Engineering — Video Editing Automation Backend Architecture</div>
    <div>Target: 1080×1920 @ 30 FPS • 900 Frames • 30.00 Seconds</div>
  </div>

<script>
  lucide.createIcons();
</script>
</body>
</html>
"""

def generate_png():
    print("Generating high-resolution architecture PNG...")
    temp_html = ROOT / "scripts" / "_temp_arch.html"
    temp_html.write_text(HTML_CONTENT, encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        # High-DPI viewport for ultra-crisp output
        page = browser.new_page(
            viewport={"width": 1800, "height": 1300},
            device_scale_factor=2,  # Retina 2x resolution
        )
        page.goto(f"file:///{str(temp_html).replace(os.sep, '/')}")
        page.wait_for_timeout(1000)  # Wait for Lucide icons and web fonts to render

        # Take full page screenshot
        page.screenshot(path=str(OUTPUT_PNG), full_page=True)
        page.screenshot(path=str(REPORTS_PNG), full_page=True)
        browser.close()

    if temp_html.exists():
        temp_html.unlink()

    size_kb = OUTPUT_PNG.stat().st_size / 1024
    print(f"Architecture diagram PNG successfully saved:")
    print(f"  -> {OUTPUT_PNG} ({size_kb:.1f} KB)")
    print(f"  -> {REPORTS_PNG} ({size_kb:.1f} KB)")

if __name__ == "__main__":
    generate_png()
