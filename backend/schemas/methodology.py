"""Pydantic schemas for Methodology and System Specifications."""

from typing import Any, Dict, List

from pydantic import BaseModel


class MetricEvaluation(BaseModel):
    metric: str
    evaluation_score: str
    baseline_random: str
    validation_set_description: str


class PipelineStage(BaseModel):
    stage_id: str
    title: str
    description: str
    badge: str
    icon: str
    details: str


class SystemLimitation(BaseModel):
    id: str
    title: str
    description: str
    policy: str
    policy_badge: str


class MethodologyResponse(BaseModel):
    version: str
    status: str
    pipeline_stages: List[PipelineStage]
    performance_metrics: List[MetricEvaluation]
    dataset_split: Dict[str, Any]
    limitations: List[SystemLimitation]
    architecture_stack: Dict[str, str]
