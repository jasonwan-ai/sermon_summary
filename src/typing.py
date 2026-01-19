# Pydantic model to constrict the return 

from pydantic import BaseModel, Field
from typing import List


class BibleVerse(BaseModel):
    verse: str = Field(description="The verse Chapter and verse number")
    reference: str = Field(description="The reference to the sermon content")


class SermonSummary(BaseModel):
    summary_markdown: str
    bible_verses: List[BibleVerse] = Field(default_factory=list)


class TimestampResponse(BaseModel):
    start_time: float
    end_time: float
    reason: str