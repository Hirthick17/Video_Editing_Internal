"""
Layer 02 — Editing Script Agent
Hirthick's Vision Studio Backend

Provides:
  - TakeSelector       : Best-take selector via energy/clarity/pacing scoring
  - StockClipDownloader: Pexels + Pixabay stock clip search and download
  - TypographyMapper   : Caption event type assignment
  - EditingScriptAgent : Orchestrates all three sub-agents
"""

from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Local imports — graceful fallbacks so this module works even before
# Layer 00 (philosophy) is committed.
# ---------------------------------------------------------------------------
try:
    from app.philosophy import EditingPhilosophy, philosophy as _default_philosophy
except ImportError:  # Layer 00 not yet present — define a minimal stand-in
    class EditingPhilosophy(BaseModel):  # type: ignore[no-redef]
        font_family: str = "Poppins"
        font_weight_primary: int = 700
        font_weight_body: int = 400
        text_case: str = "sentence_case"
        caption_style: str = "word_reveal"
        max_stock_clips: int = 2
        stock_sources: List[str] = ["pexels", "pixabay"]
        no_cinematic_lut: bool = True
        no_aggressive_jump_cuts: bool = True
        no_svg_cards: bool = True
        no_ai_diffusion: bool = True
        no_zoom_cut_combo: bool = True
        min_cut_duration_frames: int = 45
        bgm_duck_db: float = -18.0
        narration_target_wpm: tuple = (110, 150)
        accent_color_hex: str = "#25D366"
        accent_color_name: str = "WhatsApp Green"
        typography_first: bool = True

    _default_philosophy = EditingPhilosophy()

try:
    from app.state.models import (
        AssetRecord,
        ScriptRecord,
        ShotPlanRecord,
        TranscriptionRecord,
        TranscriptionWord,
        utc_now_iso,
    )
except ImportError:
    # Minimal stand-ins for isolated testing
    def utc_now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()

    class TranscriptionWord(BaseModel):  # type: ignore[no-redef]
        word: str
        start_seconds: float
        end_seconds: float
        confidence: float = 1.0

    class TranscriptionRecord(BaseModel):  # type: ignore[no-redef]
        asset_id: str
        text: str = ""
        language: str = "en"
        words: List[TranscriptionWord] = Field(default_factory=list)
        created_at_utc: str = Field(default_factory=utc_now_iso)

    class AssetRecord(BaseModel):  # type: ignore[no-redef]
        asset_id: str
        path: str
        checksum_sha256: str = ""
        asset_type: str = "VIDEO"
        metadata: Dict = Field(default_factory=dict)
        notes: str = ""
        discovered_at_utc: str = Field(default_factory=utc_now_iso)

    class ScriptRecord(BaseModel):  # type: ignore[no-redef]
        version: int = 1
        hook_text: str = ""
        problem_text: str = ""
        solution_text: str = ""
        cta_text: str = ""
        full_narration: str = ""
        claims: List[str] = Field(default_factory=list)
        word_count: int = 0
        estimated_duration_seconds: float = 0.0
        created_at_utc: str = Field(default_factory=utc_now_iso)

    class ShotPlanRecord(BaseModel):  # type: ignore[no-redef]
        version: int = 1
        shots: List = Field(default_factory=list)
        total_target_duration_seconds: float = 30.0
        coverage_percentage: float = 0.0
        created_at_utc: str = Field(default_factory=utc_now_iso)


# ===========================================================================
# PART A — Take Selector
# ===========================================================================

class TakeEvaluation(BaseModel):
    take_id: str
    asset_path: str
    transcription_text: str
    energy_score: float          # 0.0–10.0
    clarity_score: float         # 0.0–10.0
    pacing_score: float          # WPM within 110-150 → 10.0
    overall_score: float         # weighted average
    selected: bool = False
    rejection_reason: str = ""


class TakeSelectionResult(BaseModel):
    evaluated_takes: List[TakeEvaluation]
    selected_take_id: str
    selected_asset_path: str
    selection_reason: str
    evaluated_at_utc: str


class TakeSelector:
    """Scores and ranks takes using transcription clarity, pacing, and energy."""

    # ---- scoring helpers ---------------------------------------------------

    @staticmethod
    def _compute_clarity_score(words: List[TranscriptionWord]) -> float:
        """Average word confidence → 0–10 scale."""
        if not words:
            return 0.0
        avg_conf = sum(w.confidence for w in words) / len(words)
        return round(avg_conf * 10.0, 3)

    @staticmethod
    def _compute_energy_score(words: List[TranscriptionWord]) -> float:
        """Fraction of words with confidence > 0.85, × 10."""
        if not words:
            return 0.0
        high_conf = sum(1 for w in words if w.confidence > 0.85)
        return round((high_conf / len(words)) * 10.0, 3)

    @staticmethod
    def _compute_pacing_score(words: List[TranscriptionWord]) -> float:
        """
        Score based on WPM relative to the target range 110–150 WPM.
        110–150 → 10.0  |  below 110 → linear scale-down  |  above 150 → linear scale-down
        """
        if not words:
            return 0.0

        # Duration from first word start to last word end
        start = words[0].start_seconds
        end = words[-1].end_seconds
        duration_minutes = (end - start) / 60.0
        if duration_minutes <= 0:
            return 5.0  # neutral default

        wpm = len(words) / duration_minutes
        lo, hi = 110.0, 150.0

        if lo <= wpm <= hi:
            return 10.0
        elif wpm < lo:
            # Linear: at wpm=0 → score=0; at wpm=110 → score=10
            return round(max(0.0, (wpm / lo) * 10.0), 3)
        else:
            # Linear: at wpm=150 → score=10; penalise above 150
            # halve every 50 WPM above ceiling
            excess = wpm - hi
            penalty = excess / 50.0  # each 50 WPM over = -1.0 point (max 10)
            return round(max(0.0, 10.0 - penalty * 10.0), 3)

    # ---- public API --------------------------------------------------------

    def evaluate_take(
        self,
        asset: AssetRecord,
        transcription: TranscriptionRecord,
    ) -> TakeEvaluation:
        """Return a scored TakeEvaluation for one asset + transcription pair."""
        words = transcription.words

        clarity = self._compute_clarity_score(words)
        energy = self._compute_energy_score(words)
        pacing = self._compute_pacing_score(words)
        overall = round((clarity * 0.4) + (energy * 0.3) + (pacing * 0.3), 4)

        return TakeEvaluation(
            take_id=asset.asset_id,
            asset_path=asset.path,
            transcription_text=transcription.text,
            clarity_score=clarity,
            energy_score=energy,
            pacing_score=pacing,
            overall_score=overall,
        )

    def select_best_take(self, evaluations: List[TakeEvaluation]) -> TakeEvaluation:
        """Return the highest-scoring evaluation, marking it as selected."""
        if not evaluations:
            raise ValueError("No evaluations provided to select_best_take")
        best = max(evaluations, key=lambda e: e.overall_score)
        best.selected = True
        return best

    def run_take_selection(
        self,
        assets: Dict[str, AssetRecord],
        transcriptions: Dict[str, TranscriptionRecord],
    ) -> TakeSelectionResult:
        """Full pipeline: evaluate all takes, select the best one."""
        evaluations: List[TakeEvaluation] = []
        for asset_id, asset in assets.items():
            if asset_id in transcriptions:
                evaluation = self.evaluate_take(asset, transcriptions[asset_id])
                evaluations.append(evaluation)

        if not evaluations:
            # Fallback: single dummy evaluation when no data is available
            dummy = TakeEvaluation(
                take_id="take_000",
                asset_path="",
                transcription_text="",
                energy_score=0.0,
                clarity_score=0.0,
                pacing_score=0.0,
                overall_score=0.0,
                selected=True,
                rejection_reason="No takes available",
            )
            return TakeSelectionResult(
                evaluated_takes=[dummy],
                selected_take_id="take_000",
                selected_asset_path="",
                selection_reason="No takes were available for evaluation",
                evaluated_at_utc=utc_now_iso(),
            )

        best = self.select_best_take(evaluations)
        reason = (
            f"Selected take '{best.take_id}' with overall score "
            f"{best.overall_score:.3f} "
            f"(clarity={best.clarity_score:.2f}, "
            f"energy={best.energy_score:.2f}, "
            f"pacing={best.pacing_score:.2f})"
        )
        return TakeSelectionResult(
            evaluated_takes=evaluations,
            selected_take_id=best.take_id,
            selected_asset_path=best.asset_path,
            selection_reason=reason,
            evaluated_at_utc=utc_now_iso(),
        )


# ===========================================================================
# PART B — Stock Clip Downloader
# ===========================================================================

class StockClipQuery(BaseModel):
    keywords: List[str]
    max_clips: int = 2
    orientation: str = "portrait"
    min_duration_seconds: int = 3
    sources: List[str] = Field(default_factory=lambda: ["pexels", "pixabay"])


class StockClipResult(BaseModel):
    clip_id: str
    source: str                     # "pexels" or "pixabay"
    title: str
    url: str
    download_url: str
    duration_seconds: float
    width: int
    height: int
    local_path: str = ""
    downloaded: bool = False
    keyword_matched: str = ""


# Simple English stop-word list (no external deps)
_STOPWORDS = frozenset(
    "a an the and or but in on at to for of with by from is are was were be been "
    "being have has had do does did will would could should may might shall not "
    "i me my we our you your he she it its they them their this that these those "
    "as if so just also than then when where which who whom how all any both each "
    "few more most other some such no only same too very can what while about "
    "into through during before after above below between out up down off over "
    "under again further than once".split()
)


class StockClipDownloader:
    """Searches Pexels and Pixabay for stock b-roll and downloads up to max_clips."""

    # ---- keyword extraction -----------------------------------------------

    def extract_keywords(self, script: ScriptRecord) -> List[str]:
        """
        Simple keyword extraction:
          1. Tokenise the full narration (or hook+problem+solution if no narration).
          2. Lower-case, remove punctuation, drop stop-words and short tokens.
          3. Return top 5 by frequency.
        """
        text = script.full_narration or " ".join(
            filter(None, [script.hook_text, script.problem_text, script.solution_text])
        )
        # Tokenise
        tokens = re.findall(r"[a-zA-Z']+", text.lower())
        # Filter stopwords and short words
        tokens = [t.strip("'") for t in tokens if t not in _STOPWORDS and len(t) > 3]
        # Count frequency
        freq: Dict[str, int] = {}
        for tok in tokens:
            freq[tok] = freq.get(tok, 0) + 1
        # Sort by frequency desc, take top 5
        sorted_words = sorted(freq, key=lambda w: freq[w], reverse=True)
        return sorted_words[:5]

    # ---- API search helpers -----------------------------------------------

    def search_pexels(
        self,
        keywords: List[str],
        api_key: str = "",
    ) -> List[StockClipResult]:
        """
        Search Pexels for portrait video clips matching keywords.
        Returns mock results when no API key is provided.
        """
        results: List[StockClipResult] = []
        for idx, kw in enumerate(keywords):
            url = (
                f"https://api.pexels.com/videos/search"
                f"?query={kw}&orientation=portrait&per_page=3"
            )
            if not api_key:
                results.append(
                    StockClipResult(
                        clip_id=f"pexels_mock_{idx}_{kw}",
                        source="pexels",
                        title=f"[Pexels mock] {kw}",
                        url=url,
                        download_url="",
                        duration_seconds=10.0,
                        width=1080,
                        height=1920,
                        local_path="PEXELS_API_KEY not configured — mock result",
                        downloaded=False,
                        keyword_matched=kw,
                    )
                )
            else:
                try:
                    req = urllib.request.Request(
                        url, headers={"Authorization": api_key}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                    for video in data.get("videos", [])[:3]:
                        files = video.get("video_files", [])
                        dl_url = files[0]["link"] if files else ""
                        results.append(
                            StockClipResult(
                                clip_id=f"pexels_{video['id']}",
                                source="pexels",
                                title=video.get("url", kw),
                                url=video.get("url", url),
                                download_url=dl_url,
                                duration_seconds=float(video.get("duration", 0)),
                                width=video.get("width", 1080),
                                height=video.get("height", 1920),
                                keyword_matched=kw,
                            )
                        )
                except Exception:
                    # Network failure → fall back to mock
                    results.append(
                        StockClipResult(
                            clip_id=f"pexels_err_{idx}_{kw}",
                            source="pexels",
                            title=f"[Pexels error] {kw}",
                            url=url,
                            download_url="",
                            duration_seconds=10.0,
                            width=1080,
                            height=1920,
                            local_path="PEXELS_API_KEY not configured — mock result",
                            downloaded=False,
                            keyword_matched=kw,
                        )
                    )
        return results

    def search_pixabay(
        self,
        keywords: List[str],
        api_key: str = "",
    ) -> List[StockClipResult]:
        """
        Search Pixabay for vertical video clips matching keywords.
        Returns mock results when no API key is provided.
        """
        results: List[StockClipResult] = []
        for idx, kw in enumerate(keywords):
            url = (
                f"https://pixabay.com/api/videos/"
                f"?key={api_key}&q={kw}&orientation=vertical"
            )
            if not api_key:
                results.append(
                    StockClipResult(
                        clip_id=f"pixabay_mock_{idx}_{kw}",
                        source="pixabay",
                        title=f"[Pixabay mock] {kw}",
                        url=f"https://pixabay.com/api/videos/?q={kw}&orientation=vertical",
                        download_url="",
                        duration_seconds=8.0,
                        width=1080,
                        height=1920,
                        local_path="PIXABAY_API_KEY not configured — mock result",
                        downloaded=False,
                        keyword_matched=kw,
                    )
                )
            else:
                try:
                    req = urllib.request.Request(url)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                    for hit in data.get("hits", [])[:3]:
                        videos = hit.get("videos", {})
                        medium = videos.get("medium", {})
                        dl_url = medium.get("url", "")
                        results.append(
                            StockClipResult(
                                clip_id=f"pixabay_{hit['id']}",
                                source="pixabay",
                                title=hit.get("tags", kw),
                                url=hit.get("pageURL", url),
                                download_url=dl_url,
                                duration_seconds=float(hit.get("duration", 0)),
                                width=medium.get("width", 1080),
                                height=medium.get("height", 1920),
                                keyword_matched=kw,
                            )
                        )
                except Exception:
                    results.append(
                        StockClipResult(
                            clip_id=f"pixabay_err_{idx}_{kw}",
                            source="pixabay",
                            title=f"[Pixabay error] {kw}",
                            url=url,
                            download_url="",
                            duration_seconds=8.0,
                            width=1080,
                            height=1920,
                            local_path="PIXABAY_API_KEY not configured — mock result",
                            downloaded=False,
                            keyword_matched=kw,
                        )
                    )
        return results

    # ---- download ---------------------------------------------------------

    def download_clip(
        self,
        result: StockClipResult,
        output_dir: Path,
    ) -> StockClipResult:
        """
        Download a clip to output_dir.
        If the clip has no real download_url (mock), set local_path to a mock path.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_title = re.sub(r"[^\w\-]", "_", result.title)[:60]
        filename = f"{result.source}_{result.clip_id}_{safe_title}.mp4"
        dest = output_dir / filename

        if not result.download_url or result.downloaded is False and not result.download_url:
            result.local_path = str(dest) + " [mock — not downloaded]"
            return result

        # Only attempt a real download if we have a non-empty, non-mock URL
        if result.download_url and not result.downloaded:
            try:
                urllib.request.urlretrieve(result.download_url, dest)
                result.local_path = str(dest)
                result.downloaded = True
            except Exception as exc:
                result.local_path = f"{dest} [download failed: {exc}]"
        return result

    # ---- main pipeline ----------------------------------------------------

    def run(
        self,
        script: ScriptRecord,
        philosophy: EditingPhilosophy,
        output_dir: Path,
        pexels_api_key: str = "",
        pixabay_api_key: str = "",
    ) -> List[StockClipResult]:
        """
        Full pipeline:
          extract keywords → search Pexels + Pixabay → dedupe → cap at max_clips → download
        """
        keywords = self.extract_keywords(script)

        pexels_results = self.search_pexels(keywords, api_key=pexels_api_key)
        pixabay_results = self.search_pixabay(keywords, api_key=pixabay_api_key)

        # Concatenate and de-duplicate by title
        all_results = pexels_results + pixabay_results
        seen_titles: set = set()
        deduped: List[StockClipResult] = []
        for clip in all_results:
            if clip.title not in seen_titles:
                seen_titles.add(clip.title)
                deduped.append(clip)

        # Respect philosophy hard cap
        max_clips = getattr(philosophy, "max_stock_clips", 2)
        selected = deduped[:max_clips]

        # Download
        downloaded = [self.download_clip(clip, output_dir) for clip in selected]
        return downloaded


# ===========================================================================
# PART C — Typography Mapper
# ===========================================================================

class CaptionEventType(str, Enum):
    WORD_REVEAL = "word_reveal"
    QUOTE_CARD = "quote_card"
    SECTION_HEADER = "section_header"
    FADE_IN = "fade_in"


class CaptionEvent(BaseModel):
    event_id: str
    event_type: CaptionEventType
    text: str
    start_second: float
    end_second: float
    font_family: str = "Poppins"
    font_weight: int = 700
    font_size_px: int = 56
    text_case: str = "sentence_case"
    color_hex: str = "#FFFFFF"
    outline_color_hex: str = "#000000"
    outline_px: int = 4
    stagger_ms_per_word: int = 80
    accent_word: str = ""
    accent_color_hex: str = "#25D366"
    position: str = "bottom_third"


# Regex to detect quoted stats / key numbers
_STAT_PATTERN = re.compile(
    r'(?:"[^"]*[\d%][^"]*"'      # quoted string with digit or %
    r'|\d+\s*(?:tenant|user|%|→|->|rupee|lakh|crore|k\b|million))',
    re.IGNORECASE,
)


class TypographyMapper:
    """Maps script sections to typed CaptionEvent objects."""

    # ---- sentence_case helper --------------------------------------------

    @staticmethod
    def _to_sentence_case(text: str) -> str:
        if not text:
            return text
        return text[0].upper() + text[1:].lower() if len(text) > 1 else text.upper()

    # ---- event factory helpers -------------------------------------------

    @staticmethod
    def _make_section_header(
        event_id: str,
        text: str,
        start: float,
        end: float,
    ) -> CaptionEvent:
        return CaptionEvent(
            event_id=event_id,
            event_type=CaptionEventType.SECTION_HEADER,
            text=text,
            start_second=start,
            end_second=end,
            font_family="Poppins",
            font_weight=700,
            font_size_px=72,
            text_case="sentence_case",
            position="center",
        )

    @staticmethod
    def _make_word_reveal(
        event_id: str,
        text: str,
        start: float,
        end: float,
        position: str = "bottom_third",
    ) -> CaptionEvent:
        return CaptionEvent(
            event_id=event_id,
            event_type=CaptionEventType.WORD_REVEAL,
            text=text,
            start_second=start,
            end_second=end,
            font_family="Poppins",
            font_weight=700,
            font_size_px=56,
            text_case="sentence_case",
            position=position,
            stagger_ms_per_word=80,
        )

    @staticmethod
    def _make_quote_card(
        event_id: str,
        text: str,
        start: float,
        end: float,
    ) -> CaptionEvent:
        return CaptionEvent(
            event_id=event_id,
            event_type=CaptionEventType.QUOTE_CARD,
            text=text,
            start_second=start,
            end_second=end,
            font_family="Poppins",
            font_weight=700,
            font_size_px=96,
            text_case="sentence_case",
            position="center",
        )

    @staticmethod
    def _make_fade_in(
        event_id: str,
        text: str,
        start: float,
        end: float,
    ) -> CaptionEvent:
        return CaptionEvent(
            event_id=event_id,
            event_type=CaptionEventType.FADE_IN,
            text=text,
            start_second=start,
            end_second=end,
            font_family="Poppins",
            font_weight=700,
            font_size_px=56,
            text_case="sentence_case",
            position="center",
        )

    # ---- main mapping logic ----------------------------------------------

    def map_script_to_events(
        self,
        script: ScriptRecord,
        shot_plan: ShotPlanRecord,
        philosophy: EditingPhilosophy,
    ) -> List[CaptionEvent]:
        """
        Produce a list of CaptionEvent objects from a ScriptRecord.

        Mapping rules:
          • Hook text               → SECTION_HEADER  @ t=0
          • HOOK→PROBLEM transition → SECTION_HEADER
          • Problem narration       → WORD_REVEAL (one per sentence)
          • Key stats / numbers     → QUOTE_CARD
          • PROBLEM→DEMO transition → SECTION_HEADER
          • Solution text           → WORD_REVEAL
          • DEMO→SOLUTION transition→ SECTION_HEADER
          • CTA text                → FADE_IN @ t≈27s
        """
        events: List[CaptionEvent] = []
        eid = 0

        def next_id(prefix: str = "EVT") -> str:
            nonlocal eid
            eid += 1
            return f"{prefix}_{eid:03d}"

        # Short #13 script times (approximate 30s short)
        # HOOK  0–5s, PROBLEM 5–12s, DEMO 12–20s, SOLUTION 20–27s, CTA 27–30s

        # 1. Hook → SECTION_HEADER at t=0
        if script.hook_text:
            events.append(
                self._make_section_header(next_id("HOOK"), script.hook_text, 0.0, 5.0)
            )

        # 2. Transition: HOOK → PROBLEM
        events.append(
            self._make_section_header(next_id("TRANS"), "Problem", 4.5, 5.5)
        )

        # 3. Problem narration → split into sentence WORD_REVEALs
        if script.problem_text:
            sentences = [s.strip() for s in re.split(r"[.!?]+", script.problem_text) if s.strip()]
            # Allocate from t=5 to t=12 (7 seconds)
            duration_per = 7.0 / max(len(sentences), 1)
            for i, sentence in enumerate(sentences):
                start = 5.0 + i * duration_per
                end = start + duration_per

                # Check for stats inside the sentence
                stat_match = _STAT_PATTERN.search(sentence)
                if stat_match:
                    events.append(
                        self._make_quote_card(
                            next_id("STAT"),
                            stat_match.group(),
                            start,
                            end,
                        )
                    )
                else:
                    events.append(
                        self._make_word_reveal(next_id("PROB"), sentence, start, end)
                    )

        # 4. Transition: PROBLEM → DEMO
        events.append(
            self._make_section_header(next_id("TRANS"), "Demo", 11.5, 12.5)
        )

        # 5. Claims / demo stats → QUOTE_CARD
        for i, claim in enumerate(script.claims):
            start = 12.0 + i * 2.5
            end = start + 2.5
            events.append(self._make_quote_card(next_id("DEMO"), claim, start, end))

        # 6. Transition: DEMO → SOLUTION
        events.append(
            self._make_section_header(next_id("TRANS"), "Solution", 19.5, 20.5)
        )

        # 7. Solution text → WORD_REVEAL
        if script.solution_text:
            sentences = [s.strip() for s in re.split(r"[.!?]+", script.solution_text) if s.strip()]
            duration_per = 7.0 / max(len(sentences), 1)
            for i, sentence in enumerate(sentences):
                start = 20.0 + i * duration_per
                end = start + duration_per
                events.append(
                    self._make_word_reveal(next_id("SOLN"), sentence, start, end)
                )

        # 8. CTA → FADE_IN at t=27s
        if script.cta_text:
            events.append(
                self._make_fade_in(next_id("CTA"), script.cta_text, 27.0, 30.0)
            )

        return events

    def apply_philosophy(
        self,
        events: List[CaptionEvent],
        philosophy: EditingPhilosophy,
    ) -> List[CaptionEvent]:
        """
        Enforce philosophy constraints across all caption events:
          • sentence_case on all text
          • Poppins font
          • #25D366 accent colour
        """
        for event in events:
            event.font_family = getattr(philosophy, "font_family", "Poppins")
            event.text_case = getattr(philosophy, "text_case", "sentence_case")
            event.accent_color_hex = getattr(philosophy, "accent_color_hex", "#25D366")
            # Enforce sentence_case on the text itself
            if event.text:
                event.text = event.text[0].upper() + event.text[1:]
        return events

    def to_dict_list(self, events: List[CaptionEvent]) -> List[dict]:
        """Serialise CaptionEvent list to plain dicts for JSON output."""
        return [e.model_dump() for e in events]


# ===========================================================================
# Full EditingScriptAgent
# ===========================================================================

class EditingScriptOutput(BaseModel):
    take_selection: TakeSelectionResult
    stock_clips: List[StockClipResult]
    caption_events: List[CaptionEvent]
    total_caption_events: int
    generated_at_utc: str


class EditingScriptAgent:
    """
    Orchestrates TakeSelector, StockClipDownloader, and TypographyMapper.
    Saves results to reports/editing_script_output.json.
    """

    def __init__(self) -> None:
        self.take_selector = TakeSelector()
        self.stock_downloader = StockClipDownloader()
        self.typography_mapper = TypographyMapper()

    def run(
        self,
        script: ScriptRecord,
        shot_plan: ShotPlanRecord,
        assets: Dict[str, AssetRecord],
        transcriptions: Dict[str, TranscriptionRecord],
        philosophy: Optional[EditingPhilosophy] = None,
        output_dir: Optional[Path] = None,
        pexels_api_key: str = "",
        pixabay_api_key: str = "",
    ) -> EditingScriptOutput:
        """
        Run all three sub-agents in sequence, save results, return output.
        """
        if philosophy is None:
            philosophy = _default_philosophy
        if output_dir is None:
            output_dir = Path(".")

        # -- Part A: Take Selection
        take_selection = self.take_selector.run_take_selection(assets, transcriptions)

        # -- Part B: Stock Clip Download
        stock_clips = self.stock_downloader.run(
            script=script,
            philosophy=philosophy,
            output_dir=output_dir / "stock_clips",
            pexels_api_key=pexels_api_key,
            pixabay_api_key=pixabay_api_key,
        )

        # -- Part C: Typography Mapping
        caption_events = self.typography_mapper.map_script_to_events(
            script, shot_plan, philosophy
        )
        caption_events = self.typography_mapper.apply_philosophy(caption_events, philosophy)

        output = EditingScriptOutput(
            take_selection=take_selection,
            stock_clips=stock_clips,
            caption_events=caption_events,
            total_caption_events=len(caption_events),
            generated_at_utc=utc_now_iso(),
        )

        # Save to reports/
        reports_dir = output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / "editing_script_output.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(output.model_dump(), f, indent=2, default=str)

        return output


# ===========================================================================
# Short #13 — Demonstration
# ===========================================================================

def build_short13_demo() -> EditingScriptOutput:
    """
    Generate a demonstration EditingScriptOutput for Short #13
    (PG tenant management SaaS).
    """
    script = ScriptRecord(
        version=1,
        hook_text="Managing 50 PG tenants and still tracking Excel?",
        problem_text=(
            "Every month you chase rent on WhatsApp. "
            "UPI confusion leads to missed payments. "
            "50 tenants — all manual, all chaotic."
        ),
        solution_text="Tellos automates rent collection. One dashboard, zero chaos.",
        cta_text="Link in bio. Try free.",
        claims=["50 tenants → automated"],
        full_narration=(
            "Managing 50 PG tenants and still tracking Excel? "
            "Every month you chase rent on WhatsApp. "
            "UPI confusion leads to missed payments. "
            "50 tenants — all manual, all chaotic. "
            "Tellos automates rent collection. One dashboard, zero chaos. "
            "Link in bio. Try free."
        ),
        word_count=52,
        estimated_duration_seconds=30.0,
    )
    shot_plan = ShotPlanRecord(
        version=1,
        shots=[],
        total_target_duration_seconds=30.0,
    )
    assets: Dict[str, AssetRecord] = {}
    transcriptions: Dict[str, TranscriptionRecord] = {}

    agent = EditingScriptAgent()
    return agent.run(
        script=script,
        shot_plan=shot_plan,
        assets=assets,
        transcriptions=transcriptions,
        output_dir=Path("output/short_13"),
    )
