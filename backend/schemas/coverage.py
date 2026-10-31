"""Pydantic schemas for Coverage Graph, Clustering, and Publishers."""

from typing import List, Optional

from pydantic import BaseModel

from backend.schemas.articles import ArticleResponse


class RelatedArticleItem(BaseModel):
    article: ArticleResponse
    similarity: float
    relationship: str


class CoverageCluster(BaseModel):
    primary_article: ArticleResponse
    related_articles: List[RelatedArticleItem]
    publishers: List[str]
    total_coverage_count: int


class GraphNode(BaseModel):
    id: str
    label: str
    type: str  # "article" or "publisher"
    cluster_id: Optional[str] = None
    data: dict = {}


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    weight: Optional[float] = 1.0


class CoverageGraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    cluster_count: int
    article_count: int
    publisher_count: int
