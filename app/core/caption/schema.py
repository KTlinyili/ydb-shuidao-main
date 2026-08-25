from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class StrEnum(str, Enum):
    pass


class ColorEnum(StrEnum):
    green = "green"
    yellow = "yellow"
    brown = "brown"
    black = "black"
    gray = "gray"
    white = "white"
    mixed = "mixed"


class TissueStateEnum(StrEnum):
    healthy = "healthy"
    chlorosis = "chlorosis"
    necrosis = "necrosis"
    mold = "mold"
    water_soaked = "water_soaked"
    dry = "dry"


class SpotShapeEnum(StrEnum):
    round = "round"
    irregular = "irregular"
    angular = "angular"
    concentric = "concentric"
    diffuse = "diffuse"


class BoundaryEnum(StrEnum):
    clear = "clear"
    blurred = "blurred"
    yellow_halo = "yellow_halo"
    dark_ring = "dark_ring"
    no_clear_boundary = "no_clear_boundary"


class DistributionPositionEnum(StrEnum):
    lower_leaf = "lower_leaf"
    upper_leaf = "upper_leaf"
    leaf_back = "leaf_back"
    leaf_edge = "leaf_edge"
    stem = "stem"
    fruit = "fruit"
    whole_plant = "whole_plant"


class DistributionPatternEnum(StrEnum):
    scattered = "scattered"
    clustered = "clustered"
    vein_aligned = "vein_aligned"
    expanding = "expanding"
    patchy = "patchy"


class MorphChangeEnum(StrEnum):
    curling = "curling"
    wilting = "wilting"
    deformation = "deformation"
    thickening = "thickening"
    none = "none"


class PestCueEnum(StrEnum):
    insect_holes = "insect_holes"
    frass = "frass"
    webbing = "webbing"
    eggs = "eggs"
    no_obvious_pest = "no_obvious_pest"


class CoSignEnum(StrEnum):
    humidity_high = "humidity_high"
    poor_ventilation = "poor_ventilation"
    overwatering = "overwatering"
    rainy_weather = "rainy_weather"
    neighboring_outbreak = "neighboring_outbreak"
    unknown = "unknown"


class SymptomBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    color: list[ColorEnum] = Field(min_length=1)
    tissue_state: list[TissueStateEnum] = Field(min_length=1)
    spot_shape: list[SpotShapeEnum] = Field(min_length=1)
    boundary: list[BoundaryEnum] = Field(min_length=1)
    distribution_position: list[DistributionPositionEnum] = Field(min_length=1)
    distribution_pattern: list[DistributionPatternEnum] = Field(min_length=1)
    morph_change: list[MorphChangeEnum] = Field(min_length=1)
    pest_cues: list[PestCueEnum] = Field(min_length=1)
    co_signs: list[CoSignEnum] = Field(min_length=1)


class NumericBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area_ratio: float = Field(ge=0.0, le=1.0)
    severity_score: float = Field(ge=0.0, le=1.0)


class CaptionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    visual_summary: str = Field(min_length=1)
    symptoms: SymptomBlock
    numeric: NumericBlock
    confidence: float = Field(ge=0.0, le=1.0)
    ood_score: float = Field(ge=0.0, le=1.0)
    followup_questions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

