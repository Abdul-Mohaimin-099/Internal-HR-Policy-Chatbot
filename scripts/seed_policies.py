"""Seed sample HR policies from ``docs/policies`` into Postgres + Qdrant.

Run after Postgres is up and migrations applied:
    uv run python scripts/seed_policies.py
"""

from __future__ import annotations

# Disable torch.compile BEFORE any Docling / torch import (Windows needs this
# so PyTorch Inductor does not require MSVC ``cl.exe``).
import os

os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_DISABLE"] = "1"

import asyncio
from pathlib import Path

from hr_chatbot.core.database import AsyncSessionLocal
from hr_chatbot.core.logging_config import get_logger, setup_logging
from hr_chatbot.rag.ingestion import ingest_file

setup_logging()
logger = get_logger(__name__)

POLICIES_DIR = Path(__file__).resolve().parents[1] / "docs" / "policies"


async def main() -> None:
    files = sorted(POLICIES_DIR.glob("*.pdf")) + sorted(POLICIES_DIR.glob("*.md"))
    if not files:
        logger.error("No policy files found in %s", POLICIES_DIR)
        return

    logger.info(
        "torch.compile disabled (TORCHDYNAMO_DISABLE=%s)",
        os.environ.get("TORCHDYNAMO_DISABLE"),
    )

    async with AsyncSessionLocal() as session:
        for path in files:
            logger.info("Seeding %s", path.name)
            await ingest_file(session, path=path)

    logger.info("Done — indexed %s files", len(files))


if __name__ == "__main__":
    asyncio.run(main())
