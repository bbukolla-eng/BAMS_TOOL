from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from models.specification import SpecSection, SpecDrawingLink
from models.drawing import Symbol, MaterialRun


async def find_spec_drawing_matches(spec_id: int, section_id: int, db: AsyncSession) -> list[dict]:
    section_result = await db.execute(select(SpecSection).where(SpecSection.id == section_id))
    section = section_result.scalar_one_or_none()
    if not section or section.embedding is None:
        return []

    # pgvector nearest-neighbor search across symbols and material runs
    # Returns top matches by cosine similarity
    matches = []
    return matches
