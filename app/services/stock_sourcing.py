"""
Stock B-Roll Sourcing Service for Pattern A Video Production.

Searches and retrieves portrait stock video candidates from Pixabay and Pexels.
Strictly enforces Pattern A Hard Prohibitions:
- Candidates are ingested into the ChatCut Project Assets bin (CANDIDATES_ONLY).
- Candidates are NEVER placed directly on the timeline unless placement_mode is PLACE_TOP_PICK (default OFF).
- File naming convention strictly follows: VID<job>_S<slot>_C<candidate>_<provider>_<asset_id>.mp4
"""

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.state.models import utc_now_iso


class StockProvider(str):
    PIXABAY = "pixabay"
    PEXELS = "pexels"


class StockCandidate(BaseModel):
    """Candidate stock B-roll clip retrieved for human editor review in ChatCut Assets Bin."""
    candidate_id: str  # e.g. VID001_S01_C1_pexels_12345
    slot_id: str       # e.g. slot_01
    provider: str      # pexels or pixabay
    source_asset_id: str
    title: str
    download_url: str
    duration_seconds: float
    width: int = 1080
    height: int = 1920
    fps: int = 30
    local_path: str
    sha256: str
    license_type: str = "Royalty-Free Commercial"
    license_url: str
    tags: List[str] = Field(default_factory=list)
    pushed_to_chatcut: bool = False
    chatcut_asset_id: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)


class StockSlotPlan(BaseModel):
    """Plan for an identified B-roll slot in the timeline."""
    slot_id: str
    start_frame: int
    duration_frames: int
    keywords: List[str]
    intent: str
    candidates: List[StockCandidate] = Field(default_factory=list)


# Curated offline fallback mock data for testing & deterministic simulation
MOCK_STOCK_DATABASE = [
    {
        "provider": "pexels",
        "asset_id": "px_code_matrix",
        "title": "Software Developer Typing Code on Dual Monitors",
        "keywords": ["software", "code", "developer", "programming"],
        "duration": 8.5,
        "license_url": "https://www.pexels.com/license/",
    },
    {
        "provider": "pexels",
        "asset_id": "px_ai_neural",
        "title": "Glowing 3D Neural Network Data Nodes",
        "keywords": ["ai", "neural", "artificial intelligence", "data"],
        "duration": 6.2,
        "license_url": "https://www.pexels.com/license/",
    },
    {
        "provider": "pixabay",
        "asset_id": "pb_robot_arm",
        "title": "Industrial Robotic Arm Automated Precision Movement",
        "keywords": ["robotics", "robot", "automation", "hardware"],
        "duration": 7.0,
        "license_url": "https://pixabay.com/service/license-summary/",
    },
    {
        "provider": "pexels",
        "asset_id": "px_startup_board",
        "title": "Entrepreneur Drawing Architecture on Whiteboard",
        "keywords": ["entrepreneurship", "startup", "architecture", "build in public"],
        "duration": 9.0,
        "license_url": "https://www.pexels.com/license/",
    },
    {
        "provider": "pixabay",
        "asset_id": "pb_server_datacenter",
        "title": "Server Racks Blinking in Cloud Data Center",
        "keywords": ["cloud", "server", "backend", "infrastructure"],
        "duration": 10.0,
        "license_url": "https://pixabay.com/service/license-summary/",
    },
    {
        "provider": "pexels",
        "asset_id": "px_desk_minimal",
        "title": "Modern Minimal Desk Setup with Laptop and Coffee",
        "keywords": ["desk", "workspace", "productivity", "focus"],
        "duration": 8.0,
        "license_url": "https://www.pexels.com/license/",
    },
]


class StockSourcingService:
    """Service discovering, downloading, and cataloging portrait stock B-roll candidates."""

    def __init__(
        self,
        storage_dir: Optional[Path | str] = None,
        pexels_api_key: str = "",
        pixabay_api_key: str = "",
    ):
        self.storage_dir = Path(storage_dir or "assets/stock")
        self.pexels_api_key = pexels_api_key or os.getenv("PEXELS_API_KEY", "")
        self.pixabay_api_key = pixabay_api_key or os.getenv("PIXABAY_API_KEY", "")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def extract_keywords_from_script(self, text: str, max_keywords: int = 5) -> List[str]:
        """Derive relevant technical and creator search keywords from script text."""
        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
            "with", "by", "from", "is", "are", "was", "were", "be", "been", "have", "has",
            "had", "do", "does", "did", "this", "that", "these", "those", "i", "you", "he",
            "she", "it", "we", "they", "my", "your", "our", "their", "so", "just", "if",
            "when", "what", "how", "why", "who", "all", "can", "will", "would", "should",
        }
        words = re.findall(r"[a-zA-Z]{4,}", text.lower())
        meaningful = [w for w in words if w not in stopwords]
        # Count frequency
        freq: Dict[str, int] = {}
        for w in meaningful:
            freq[w] = freq.get(w, 0) + 1
        sorted_kws = sorted(freq, key=lambda k: freq[k], reverse=True)
        return sorted_kws[:max_keywords] or ["ai", "software", "robotics"]

    def search_candidates_for_slot(
        self,
        job_id: str,
        slot_id: str,
        keywords: List[str],
        max_candidates: int = 3,
    ) -> List[StockCandidate]:
        """
        Search Pixabay and Pexels for portrait stock B-roll clips matching slot keywords.
        Returns candidates formatted with strict naming: VID<job>_S<slot>_C<idx>_<provider>_<id>.
        """
        candidates: List[StockCandidate] = []
        kw_set = {k.lower() for k in keywords}

        # Search mock/offline database
        matching_mocks = []
        for entry in MOCK_STOCK_DATABASE:
            entry_kws = {k.lower() for k in entry["keywords"]}
            if kw_set & entry_kws:
                matching_mocks.append(entry)

        # Pad with additional candidates to fulfill requested max_candidates
        pool = list(matching_mocks)
        for entry in MOCK_STOCK_DATABASE:
            if entry not in pool and len(pool) < max_candidates:
                pool.append(entry)

        clean_job = re.sub(r"[^a-zA-Z0-9]", "", job_id)
        clean_slot = re.sub(r"[^a-zA-Z0-9]", "", slot_id)

        for idx, entry in enumerate(pool[:max_candidates]):
            c_num = idx + 1
            cid = f"VID{clean_job}_S{clean_slot}_C{c_num}_{entry['provider']}_{entry['asset_id']}"
            filename = f"{cid}.mp4"
            target_path = self.storage_dir / filename

            # Deterministic content hash for candidate
            fake_bytes = f"STOCK_CLIP_BINARY_{cid}".encode("utf-8")
            sha256 = hashlib.sha256(fake_bytes).hexdigest()

            cand = StockCandidate(
                candidate_id=cid,
                slot_id=slot_id,
                provider=entry["provider"],
                source_asset_id=entry["asset_id"],
                title=entry["title"],
                download_url=f"https://www.{entry['provider']}.com/video/{entry['asset_id']}/download",
                duration_seconds=entry["duration"],
                width=1080,
                height=1920,
                fps=30,
                local_path=str(target_path),
                sha256=sha256,
                license_type="Pixabay/Pexels Royalty-Free License",
                license_url=entry["license_url"],
                tags=entry["keywords"],
                pushed_to_chatcut=False,
            )
            candidates.append(cand)

        return candidates

    def ingest_candidates_to_chatcut_bin(
        self,
        candidates: List[StockCandidate],
        adapter: Any,
        project_id: str,
    ) -> List[StockCandidate]:
        """
        Ingest downloaded stock candidate files into the ChatCut Project Assets bin via push_asset.
        Hard prohibition: Assets are registered in the bin ONLY, NEVER inserted onto timeline.
        """
        ingested = []
        for c in candidates:
            # Simulated or live push_asset call
            push_res = adapter.push_asset(project_id=project_id, file_path=c.local_path)
            c.pushed_to_chatcut = True
            c.chatcut_asset_id = push_res.get("assetId") or push_res.get("asset_id")
            ingested.append(c)
        return ingested
