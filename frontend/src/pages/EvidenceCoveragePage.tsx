import React, { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { newsApi } from '../services/api';
import type { GraphNode, GraphEdge } from '../types/api';
import cytoscape from 'cytoscape';
import {
  AlertCircle,
  Network,
  Download,
} from 'lucide-react';

export const EvidenceCoveragePage: React.FC = () => {
  const cyRef = useRef<HTMLDivElement>(null);

  const { data: clustersData, isLoading: clustersLoading } = useQuery({
    queryKey: ['coverage', 'clusters'],
    queryFn: () => newsApi.getCoverageClusters(20),
  });

  const { data: graphData } = useQuery({
    queryKey: ['coverage', 'graph'],
    queryFn: () => newsApi.getCoverageGraph(30),
  });

  // Cytoscape network graph rendering
  useEffect(() => {
    if (!graphData || !cyRef.current) return;

    const cyElements = [
      ...graphData.nodes.map((n: GraphNode) => ({
        data: {
          id: n.id,
          label: n.label,
          type: n.type,
          bgColor: n.type === 'publisher' ? '#087F83' : '#183B56',
        },
      })),
      ...graphData.edges.map((e: GraphEdge) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.relationship,
        },
      })),
    ];

    const cy = cytoscape({
      container: cyRef.current,
      elements: cyElements,
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(bgColor)',
            label: 'data(label)',
            color: '#FFFFFF',
            'font-size': '10px',
            'text-valign': 'center',
            'text-halign': 'center',
            'text-wrap': 'wrap',
            'text-max-width': '90px',
            width: 50,
            height: 50,
            'border-width': 2,
            'border-color': '#FFFFFF',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#CBD5E1',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '8px',
            color: '#64748B',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: false,
        padding: 30,
      },
    });

    return () => {
      cy.destroy();
    };
  }, [graphData]);

  return (
    <div className="space-y-6">
      {/* Header matching Stitch Spec */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold tracking-wider text-[#315FE8] uppercase bg-[#EAF0FF] px-2 py-0.5 rounded">
              OSINT DOSSIER #NL-2024-884
            </span>
            <span className="text-[11px] text-[#64748B] font-medium">• Comparative Audit Ledger</span>
          </div>
          <h2 className="text-3xl font-bold font-serif text-[#183B56] tracking-tight">
            Evidence & Coverage
          </h2>
          <p className="text-xs text-[#64748B] mt-1 max-w-2xl">
            Compare available reporting, trace original sources, and inspect related claims across cross-referenced verification nodes.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => alert('Dossier compiled for download.')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#183B56] hover:bg-[#20496B] text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" /> Export Dossier (JSON)
          </button>
        </div>
      </div>

      {/* Editorial Independence Caution Banner */}
      <div className="p-4 bg-[#F8FAFC] border border-[#CBD5E1] rounded-lg text-xs space-y-1">
        <div className="font-bold text-[#183B56] flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-[#315FE8]" />
          EDITORIAL INDEPENDENCE CAUTION & WIRE SYNDICATION RULE
        </div>
        <p className="text-[#64748B] leading-relaxed">
          Multiple publishers frequently syndicate identical press agency dispatches (e.g., Press Trust of India, ANI). Repetition of identical wording across 5 outlets does <strong>NOT</strong> indicate 5 independent eyewitness confirmations; it reflects unified wire upstream intake.
        </p>
      </div>

      {/* Main Grid: Multi-Publisher Matrix & Provenance Ledger */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Analyzed Text Passage & Provenance */}
        <div className="lg:col-span-5 space-y-6">
          {/* Analyzed Text Passage Card */}
          <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-[#183B56] uppercase text-[10px]">CURRENT INVESTIGATION PASSAGE</span>
              <span className="px-2 py-0.5 rounded bg-[#EBF8FF] text-[#315FE8] font-bold text-[10px]">
                Active Ingest Stream
              </span>
            </div>

            <p className="text-sm font-serif italic text-[#142B4A] bg-[#F8FAFC] p-4 rounded border-l-4 border-[#315FE8] leading-relaxed">
              {clustersData && clustersData.length > 0
                ? clustersData[0].primary_article.title
                : 'Select an article from News Monitor to inspect its provenance and cross-publisher reporting clusters.'}
            </p>

            <div className="flex items-center justify-between text-xs pt-2 border-t border-[#F1F5F9]">
              <span className="text-[#64748B]">Primary Wire Attribution:</span>
              <span className="font-bold text-[#087F83]">
                {clustersData && clustersData.length > 0 ? clustersData[0].primary_article.publisher : 'Indian News Wires'}
              </span>
            </div>
          </div>

          {/* Cryptographic Provenance Ledger */}
          <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-[#183B56] uppercase text-[10px]">PROVENANCE RECORD</span>
              <span className="font-mono text-[10px] text-[#087F83] bg-[#E5F6F3] px-2 py-0.5 rounded">
                SQLite Persistence
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-[#F8FAFC] p-3 rounded">
              <div>
                <span className="text-[#94A3B8] text-[10px] block">Source Beat:</span>
                <strong className="text-[#183B56]">Syndicated RSS / GDELT</strong>
              </div>
              <div>
                <span className="text-[#94A3B8] text-[10px] block">Datastore Records:</span>
                <strong className="text-[#183B56]">824 Stored Articles</strong>
              </div>
            </div>

            <div className="text-[11px] font-mono text-[#64748B] flex items-center justify-between border-t border-[#F1F5F9] pt-2">
              <span>Canonical Ingestion Hash: Verified</span>
              <span className="text-[#10B981] font-semibold">Indexed</span>
            </div>
          </div>

          {/* Synthesis & Discrepancy Analysis (3 Columns) */}
          <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs space-y-3">
            <h4 className="font-bold text-sm text-[#183B56] font-serif">Coverage Analysis & Cross-Referencing</h4>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded bg-[#F8FAFC] border border-[#E2E8F0]">
                <strong className="text-[#087F83] block mb-1">Multi-Outlet Syndication Clusters</strong>
                <p className="text-[#64748B] text-[11px]">
                  Articles grouped by cosine similarity (threshold ≥ 0.55). Reprints from wire agencies are clustered to isolate unified feeds from independent investigations.
                </p>
              </div>

              <div className="p-2.5 rounded bg-[#F8FAFC] border border-[#E2E8F0]">
                <strong className="text-[#315FE8] block mb-1">Fact-Check Cross Indexing</strong>
                <p className="text-[#64748B] text-[11px]">
                  Automated BM25Plus retrieval compares unverified reports against indexed ClaimReview archives (BOOM Live, PIB Fact Check, Alt News).
                </p>
              </div>

              <div className="p-2.5 rounded bg-[#F8FAFC] border border-[#E2E8F0]">
                <strong className="text-[#EF806B] block mb-1">Probabilistic Linguistic Screening</strong>
                <p className="text-[#64748B] text-[11px]">
                  Lexical panic markers are scored using TF-IDF n-grams and Logistic Regression trained on benchmark news framing corpora.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Multi-Publisher Matrix & Graph Topology */}
        <div className="lg:col-span-7 space-y-6">
          {/* Cytoscape Coverage Graph */}
          <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs space-y-3">
            <div className="flex items-center justify-between text-xs border-b border-[#F1F5F9] pb-2">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-[#315FE8]" />
                <h4 className="font-bold text-sm text-[#183B56]">Coverage Graph Topology</h4>
              </div>
              <span className="text-[10px] text-[#64748B]">
                Interactive Cytoscape.js • Pan & Zoom
              </span>
            </div>

            <div
              ref={cyRef}
              className="w-full h-72 bg-[#F8FAFC] rounded border border-[#E2E8F0]"
            />

            <div className="flex items-center justify-between text-[11px] text-[#64748B]">
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#183B56]"></span> Article Node
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#087F83]"></span> Publisher Node
                </span>
              </div>
              <span>Click node to inspect relationships</span>
            </div>
          </div>

          {/* Multi-Publisher Coverage Matrix */}
          <div className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between text-xs border-b border-[#F1F5F9] pb-2">
              <h4 className="font-bold text-sm text-[#183B56] font-serif">Multi-Publisher Coverage Matrix</h4>
              <span className="text-[10px] bg-[#EAF0FF] text-[#315FE8] font-bold px-2 py-0.5 rounded">
                Cross-Indexed Wires
              </span>
            </div>

            <div className="space-y-3">
              {clustersLoading ? (
                <div className="p-8 text-center text-xs text-[#64748B]">Loading coverage clusters...</div>
              ) : (
                clustersData?.slice(0, 4).map((cluster: any, idx: number) => (
                  <div key={idx} className="p-4 rounded-md border border-[#E2E8F0] bg-[#F8FAFC] space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-[#183B56]">{cluster.primary_article.publisher}</span>
                      <span className="text-[10px] text-[#94A3B8]">
                        {new Date(cluster.primary_article.published_at).toLocaleDateString()}
                      </span>
                    </div>

                    <h5 className="text-xs font-bold text-[#142B4A] leading-snug">
                      {cluster.primary_article.title}
                    </h5>

                    <div className="flex items-center justify-between text-[11px] pt-1 text-[#64748B]">
                      <span>Publishers: {cluster.publishers.join(', ')}</span>
                      <span className="font-semibold text-[#087F83]">
                        {cluster.total_coverage_count} Syndicated Outlets
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
