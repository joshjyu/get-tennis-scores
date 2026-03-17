# SPDX-License-Identifier: MIT
# Copyright (c) 2026 joshjyu

from pydantic import BaseModel, Field
from typing import List, Optional


class StatusType(BaseModel):
    description: str = ""
    completed: bool = False


class Status(BaseModel):
    type: StatusType = Field(default_factory=StatusType)


class RoundInfo(BaseModel):
    displayName: str = "N/A"


class Athlete(BaseModel):
    shortName: str = "TBD"


class CuratedRank(BaseModel):
    current: Optional[int] = None


class LineScore(BaseModel):
    value: Optional[float] = None
    tiebreak: Optional[float] = None


class Competitor(BaseModel):
    athlete: Athlete = Field(default_factory=Athlete)
    curatedRank: CuratedRank = Field(default_factory=CuratedRank)
    possession: bool = False
    winner: bool = False
    linescores: List[LineScore] = Field(default_factory=list)


class Match(BaseModel):
    id: str
    status: Status = Field(default_factory=Status)
    round: RoundInfo = Field(default_factory=RoundInfo)
    competitors: List[Competitor] = Field(default_factory=list)


class GroupingMeta(BaseModel):
    slug: str = ""


class Grouping(BaseModel):
    grouping: GroupingMeta = Field(default_factory=GroupingMeta)
    competitions: List[Match] = Field(default_factory=list)


class Venue(BaseModel):
    displayName: str = "Unknown"


class Event(BaseModel):
    id: str
    name: str = "Unknown Tournament"
    venue: Venue = Field(default_factory=Venue)
    groupings: List[Grouping] = Field(default_factory=list)


class TourData(BaseModel):
    events: List[Event] = Field(default_factory=list)
