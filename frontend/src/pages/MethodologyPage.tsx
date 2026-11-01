import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { newsApi } from '../services/api';
import type { PipelineStage, MetricEvaluation, SystemLimitation } from '../types/api';
import {
  AlertTriangle,
  Download,
} from 'lucide-react';

export const MethodologyPage: React.FC = () => {
  const { data: methodology, isLoading } = useQuery({
    queryKey: ['methodology'],
    queryFn: () => newsApi.getMethodology(),
  });

  if (isLoading || !methodology) {
    return (
      <div className="p-12 text-center text-xs text-[#64748B]">
        Loading institutional architecture specifications...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header matching Stitch Spec */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold tracking-wider text-[#315FE8] uppercase bg-[#EAF0FF] px-2 py-0.5 rounded">
              INSTITUTIONAL BLUEPRINT • {methodology.version}
            </span>
            <span className="text-[11px] text-[#64748B] font-medium">• {methodology.status}</span>
          </div>
          <h2 className="text-3xl font-bold font-serif text-[#183B56] tracking-tight">
            Methodology & Data Sources
          </h2>
          <p className="text-xs text-[#64748B] mt-1 max-w-2xl">
            Technical architecture, probabilistic machine learning pipeline, curated dataset corpora, and empirical limitations governing the Indian Media Observatory screening framework.
          </p>
        </div>

        <button
          onClick={() => alert('Institutional Whitepaper PDF compiled.')}
          className="flex items-center gap-1.5 px-4 py-2 bg-[#183B56] hover:bg-[#20496B] text-white rounded-md text-xs font-semibold shadow-xs cursor-pointer"
        >
          <Download className="w-3.5 h-3.5" /> Export Whitepaper (PDF)
        </button>
      </div>

      {/* 4-Stage Architecture Cards matching Stitch */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {methodology.pipeline_stages.map((stage: PipelineStage) => (
          <div
            key={stage.stage_id}
            className="bg-white p-5 rounded-lg border border-[#E2E8F0] shadow-xs flex flex-col justify-between space-y-3"
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="px-2 py-0.5 rounded bg-[#EAF0FF] text-[#315FE8] text-[10px] font-bold">
                  {stage.badge}
                </span>
                <span className="text-lg text-[#183B56]">⚙️</span>
              </div>
              <h3 className="font-bold text-base text-[#183B56] font-serif leading-snug">
                {stage.title}
              </h3>
              <p className="text-xs text-[#64748B] leading-relaxed mt-2">{stage.description}</p>
            </div>
            <div className="pt-2 border-t border-[#F1F5F9] text-[11px] font-semibold text-[#087F83]">
              {stage.details}
            </div>
          </div>
        ))}
      </div>

      {/* Model Performance Table & Dataset Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Performance Table */}
        <div className="lg:col-span-7 bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
            <div>
              <h3 className="font-bold text-base text-[#183B56] font-serif">
                Model Performance & Calibration
              </h3>
              <p className="text-[11px] text-[#94A3B8]">
                Empirical validation metrics across multi-fold stratified Indian media splits
              </p>
            </div>
            <span className="px-2 py-0.5 rounded bg-[#E5F6F3] text-[#087F83] text-[10px] font-bold">
              Validation v2.1
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#E2E8F0] text-[10px] text-[#64748B] uppercase tracking-wider">
                  <th className="pb-2 font-bold">METRIC</th>
                  <th className="pb-2 font-bold">EVALUATION SCORE</th>
                  <th className="pb-2 font-bold">BASELINE RANDOM</th>
                  <th className="pb-2 font-bold">VALIDATION SET DESCRIPTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F5F9]">
                {methodology.performance_metrics.map((pm: MetricEvaluation, idx: number) => (
                  <tr key={idx} className="hover:bg-[#F8FAFC]">
                    <td className="py-2.5 font-bold text-[#183B56]">{pm.metric}</td>
                    <td className="py-2.5 font-bold text-[#087F83] tabular-nums">{pm.evaluation_score}</td>
                    <td className="py-2.5 text-[#94A3B8] tabular-nums">{pm.baseline_random}</td>
                    <td className="py-2.5 text-[#64748B] text-[11px]">{pm.validation_set_description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="p-3 bg-[#F8F9FF] border border-[#D9E3F6] rounded text-[11px] text-[#475569] leading-relaxed">
            <strong>ℹ️ Methodological Caveat:</strong> Evaluation figures represent experimental test-bench validation; live production metrics depend on real-world news drift, adversarial phrasing, and domain novelty.
          </div>
        </div>

        {/* Dataset Corpus Split */}
        <div className="lg:col-span-5 bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
          <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
            <h3 className="font-bold text-base text-[#183B56] font-serif">Dataset Corpus Split</h3>
            <span className="text-[10px] text-[#94A3B8]">Curated benchmark composition</span>
          </div>

          <div className="flex flex-col items-center justify-center p-4">
            <div className="w-32 h-32 rounded-full border-12 border-[#183B56] border-t-[#087F83] border-r-[#27C6C1] flex flex-col items-center justify-center">
              <span className="text-xl font-bold text-[#183B56] font-serif tabular-nums">
                {methodology.dataset_split.total_articles.toLocaleString()}
              </span>
              <span className="text-[10px] uppercase text-[#64748B]">Samples</span>
            </div>
          </div>

          <div className="space-y-2 text-xs">
            {methodology.dataset_split.segments.map((seg: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-[#F8FAFC]">
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      i === 0 ? 'bg-[#183B56]' : i === 1 ? 'bg-[#087F83]' : 'bg-[#27C6C1]'
                    }`}
                  ></span>
                  <span className="text-[#183B56] font-medium">{seg.label}</span>
                </div>
                <div className="text-right">
                  <strong className="text-[#183B56]">{seg.percentage}%</strong>{' '}
                  <span className="text-[#94A3B8]">({seg.count.toLocaleString()})</span>
                </div>
              </div>
            ))}
          </div>

          <div className="text-[11px] text-center text-[#94A3B8] pt-2 border-t border-[#F1F5F9]">
            Stratified sampling interval: {methodology.dataset_split.sampling_interval}
          </div>
        </div>
      </div>

      {/* 6 System Limitations & Ethical Principles matching Stitch */}
      <div className="bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
          <div>
            <h3 className="font-bold text-lg text-[#183B56] font-serif">
              System Limitations & Ethical Principles
            </h3>
            <p className="text-xs text-[#64748B]">
              Core scientific constraints governing safe deployment in investigative media workflows
            </p>
          </div>
          <span className="px-2.5 py-1 bg-[#EAF0FF] text-[#315FE8] text-[10px] font-bold rounded">
            Ethical AI Framework v1.0
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {methodology.limitations.map((lim: SystemLimitation) => (
            <div
              key={lim.id}
              className="p-4 rounded-md border border-[#E2E8F0] bg-[#F8FAFC] space-y-2 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <AlertTriangle className="w-4 h-4 text-[#D97706]" />
                  <h4 className="font-bold text-xs text-[#183B56]">{lim.title}</h4>
                </div>
                <p className="text-xs text-[#64748B] leading-relaxed">{lim.description}</p>
              </div>

              <div className="pt-2 border-t border-[#E2E8F0] flex items-center justify-between text-[10px]">
                <span className="text-[#94A3B8]">Compliance Policy:</span>
                <span className="font-bold text-[#087F83]">{lim.policy}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
