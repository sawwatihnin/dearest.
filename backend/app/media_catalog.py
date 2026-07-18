"""Curated local media catalog for semantic song and movie recommendations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MediaItem:
    kind: str
    title: str
    creator: str
    year: int
    link: str
    artwork_hint: str
    themes: tuple[str, ...]
    emotions: tuple[str, ...]
    tone: str
    description: str


MEDIA_CATALOG: tuple[MediaItem, ...] = (
    MediaItem(
        kind="song",
        title="I Know the End",
        creator="Phoebe Bridgers",
        year=2020,
        link="https://www.google.com/search?q=Phoebe+Bridgers+I+Know+the+End",
        artwork_hint="Midnight blue horizon",
        themes=("distance", "change", "memory", "longing"),
        emotions=("longing", "nostalgia", "grief"),
        tone="haunted",
        description="A slow-burning song about endings, memory, and the ache of watching a life change shape.",
    ),
    MediaItem(
        kind="song",
        title="Liability",
        creator="Lorde",
        year=2017,
        link="https://www.google.com/search?q=Lorde+Liability",
        artwork_hint="Soft gold portrait",
        themes=("identity", "isolation", "heartbreak"),
        emotions=("heartbreak", "confusion", "grief"),
        tone="bare",
        description="A stripped-down confession about feeling too much and carrying your own loneliness.",
    ),
    MediaItem(
        kind="song",
        title="Nightswimming",
        creator="R.E.M.",
        year=1992,
        link="https://www.google.com/search?q=REM+Nightswimming",
        artwork_hint="Black water with silver light",
        themes=("memory", "past", "summer", "belonging"),
        emotions=("nostalgia", "love", "longing"),
        tone="reflective",
        description="A tender meditation on memory, youth, and the shimmering distance between now and then.",
    ),
    MediaItem(
        kind="song",
        title="The Night We Met",
        creator="Lord Huron",
        year=2015,
        link="https://www.google.com/search?q=Lord+Huron+The+Night+We+Met",
        artwork_hint="Dusky forest silhouette",
        themes=("regret", "loss", "memory", "heartbreak"),
        emotions=("heartbreak", "longing", "grief"),
        tone="wistful",
        description="A song suspended in regret, asking what was lost and whether anything could have been saved.",
    ),
    MediaItem(
        kind="song",
        title="Fast Car",
        creator="Tracy Chapman",
        year=1988,
        link="https://www.google.com/search?q=Tracy+Chapman+Fast+Car",
        artwork_hint="Road at dusk",
        themes=("escape", "home", "hope", "family"),
        emotions=("healing", "confusion", "hope"),
        tone="restless",
        description="A story-song about escape, inheritance, and the stubborn desire for a different life.",
    ),
    MediaItem(
        kind="song",
        title="Motion Sickness",
        creator="Phoebe Bridgers",
        year=2017,
        link="https://www.google.com/search?q=Phoebe+Bridgers+Motion+Sickness",
        artwork_hint="Peach dusk and moving lights",
        themes=("betrayal", "distance", "recovery"),
        emotions=("anger", "healing", "heartbreak"),
        tone="clear-eyed",
        description="A sharp, emotionally precise song about betrayal, aftermath, and trying to move forward anyway.",
    ),
    MediaItem(
        kind="movie",
        title="Eternal Sunshine of the Spotless Mind",
        creator="Michel Gondry",
        year=2004,
        link="https://www.google.com/search?q=Eternal+Sunshine+of+the+Spotless+Mind",
        artwork_hint="Snow over blue memory",
        themes=("memory", "loss", "change", "love"),
        emotions=("longing", "heartbreak", "healing"),
        tone="dreamlike",
        description="A film about memory, irreversible change, and the question of whether pain is worth erasing.",
    ),
    MediaItem(
        kind="movie",
        title="Past Lives",
        creator="Celine Song",
        year=2023,
        link="https://www.google.com/search?q=Past+Lives+film",
        artwork_hint="City lights over water",
        themes=("distance", "identity", "memory", "love"),
        emotions=("longing", "nostalgia", "love"),
        tone="tender",
        description="A quiet story about distance, alternate futures, and the emotional life of what never fully leaves us.",
    ),
    MediaItem(
        kind="movie",
        title="Lost in Translation",
        creator="Sofia Coppola",
        year=2003,
        link="https://www.google.com/search?q=Lost+in+Translation+film",
        artwork_hint="Neon haze at night",
        themes=("isolation", "connection", "change", "distance"),
        emotions=("longing", "confusion", "nostalgia"),
        tone="atmospheric",
        description="A lonely, intimate film about fleeting connection and the strange tenderness of being misunderstood.",
    ),
    MediaItem(
        kind="movie",
        title="Aftersun",
        creator="Charlotte Wells",
        year=2022,
        link="https://www.google.com/search?q=Aftersun+film",
        artwork_hint="Faded holiday light",
        themes=("family", "memory", "grief", "growing older"),
        emotions=("grief", "nostalgia", "love"),
        tone="fragile",
        description="A memory-framed portrait of love, grief, and the parts of family life we only understand later.",
    ),
    MediaItem(
        kind="movie",
        title="Moonlight",
        creator="Barry Jenkins",
        year=2016,
        link="https://www.google.com/search?q=Moonlight+film",
        artwork_hint="Blue portrait in shadow",
        themes=("identity", "belonging", "love", "growing up"),
        emotions=("confusion", "love", "healing"),
        tone="intimate",
        description="A lyrical coming-of-age story about identity, tenderness, and finding a language for the self.",
    ),
    MediaItem(
        kind="movie",
        title="Manchester by the Sea",
        creator="Kenneth Lonergan",
        year=2016,
        link="https://www.google.com/search?q=Manchester+by+the+Sea",
        artwork_hint="Cold shoreline gray",
        themes=("grief", "family", "regret", "home"),
        emotions=("grief", "heartbreak", "nostalgia"),
        tone="raw",
        description="A devastating film about grief, family responsibility, and living beside pain that does not fully leave.",
    ),
)
