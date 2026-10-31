"""Coverage clustering, syndication detection, and graph topology API routes."""

from typing import List

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_news_service
from backend.schemas.articles import ArticleResponse
from backend.schemas.common import APIResponse
from backend.schemas.coverage import (
    CoverageCluster,
    CoverageGraphResponse,
    GraphEdge,
    GraphNode,
    RelatedArticleItem,
)
from src.services.news_service import NewsLensService

router = APIRouter(prefix="/coverage", tags=["Coverage"])


@router.get("/clusters", response_model=APIResponse[List[CoverageCluster]])
def get_coverage_clusters(
    limit: int = Query(50, ge=5, le=100),
    service: NewsLensService = Depends(get_news_service),
):
    """Calculates multi-publisher story clusters and syndication networks."""
    articles = service.get_recent_articles(limit=limit)
    raw_clusters = service.analyze_coverage_clusters(articles)

    clusters = []
    for c in raw_clusters:
        pa = c["primary_article"]
        primary = ArticleResponse(
            id=pa.id,
            title=pa.title,
            url=pa.url,
            publisher=pa.publisher,
            published_at=pa.published_at,
            ingested_at=pa.ingested_at,
            source_type=pa.source_type,
            summary=pa.summary or "",
            language=pa.language,
            country=pa.country,
            query=pa.query,
        )

        related = []
        for r in c.get("related_articles", []):
            ra = r["article"]
            related.append(
                RelatedArticleItem(
                    article=ArticleResponse(
                        id=ra.id,
                        title=ra.title,
                        url=ra.url,
                        publisher=ra.publisher,
                        published_at=ra.published_at,
                        ingested_at=ra.ingested_at,
                        source_type=ra.source_type,
                        summary=ra.summary or "",
                        language=ra.language,
                        country=ra.country,
                        query=ra.query,
                    ),
                    similarity=float(r["similarity"]),
                    relationship=r["relationship"],
                )
            )

        clusters.append(
            CoverageCluster(
                primary_article=primary,
                related_articles=related,
                publishers=c.get("publishers", []),
                total_coverage_count=c.get("total_coverage_count", 1),
            )
        )

    return APIResponse(data=clusters)


@router.get("/graph", response_model=APIResponse[CoverageGraphResponse])
def get_coverage_graph(
    limit: int = Query(40, ge=10, le=100),
    service: NewsLensService = Depends(get_news_service),
):
    """Produces Cytoscape-compatible node and edge topology from real clustering data."""
    articles = service.get_recent_articles(limit=limit)
    raw_clusters = service.analyze_coverage_clusters(articles)

    nodes: List[GraphNode] = []
    edges: List[GraphEdge] = []
    seen_nodes = set()
    seen_publishers = set()

    for idx, cluster in enumerate(raw_clusters):
        cid = f"cluster_{idx}"
        pa = cluster["primary_article"]

        # Primary article node
        if pa.id not in seen_nodes:
            seen_nodes.add(pa.id)
            nodes.append(
                GraphNode(
                    id=pa.id,
                    label=pa.title[:45] + "..." if len(pa.title) > 45 else pa.title,
                    type="article",
                    cluster_id=cid,
                    data={"title": pa.title, "publisher": pa.publisher, "url": pa.url},
                )
            )

        # Publisher node
        pub_id = f"pub_{pa.publisher.replace(' ', '_').lower()}"
        if pub_id not in seen_nodes:
            seen_nodes.add(pub_id)
            seen_publishers.add(pa.publisher)
            nodes.append(
                GraphNode(
                    id=pub_id,
                    label=pa.publisher,
                    type="publisher",
                    cluster_id=cid,
                    data={"publisher": pa.publisher},
                )
            )
        edges.append(
            GraphEdge(
                id=f"{pa.id}_{pub_id}",
                source=pa.id,
                target=pub_id,
                relationship="published_by",
                weight=1.0,
            )
        )

        for rel in cluster.get("related_articles", []):
            ra = rel["article"]
            if ra.id not in seen_nodes:
                seen_nodes.add(ra.id)
                nodes.append(
                    GraphNode(
                        id=ra.id,
                        label=ra.title[:45] + "..." if len(ra.title) > 45 else ra.title,
                        type="article",
                        cluster_id=cid,
                        data={"title": ra.title, "publisher": ra.publisher, "url": ra.url},
                    )
                )

            # Article-to-article similarity edge
            edges.append(
                GraphEdge(
                    id=f"{pa.id}_{ra.id}",
                    source=pa.id,
                    target=ra.id,
                    relationship=rel["relationship"],
                    weight=float(rel["similarity"]),
                )
            )

    return APIResponse(
        data=CoverageGraphResponse(
            nodes=nodes,
            edges=edges,
            cluster_count=len(raw_clusters),
            article_count=len([n for n in nodes if n.type == "article"]),
            publisher_count=len(seen_publishers),
        )
    )
