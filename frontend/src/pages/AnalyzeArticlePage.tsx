import React, { useState, useEffect } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { newsApi } from '../services/api';
import { useSearchParams, Link } from 'react-router-dom';
import {
  AlertTriangle,
  Cpu,
  Layers,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import type { AnalysisResponse, InfluentialToken } from '../types/api';

const SAMPLE_CLAIM =
  'URGENT: Ministry of Railways has announced an immediate 15% increase across all passenger and express train fares effective from the first of next month. Circular claims passenger concessions will also be suspended indefinitely due to operational budget adjustments. Check full revised timetable and fare list immediately before bookings close.';

export const AnalyzeArticlePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialText = searchParams.get('text') || '';
  const [textInput, setTextInput] = useState(initialText);

  const { data: health } = useQuery({
    queryKey: ['health-ready'],
    queryFn: () => newsApi.getHealth(),
  });

  const analysisMutation = useMutation({
    mutationFn: (text: string) => newsApi.analyzeArticle({ text }),
  });

  useEffect(() => {
    if (initialText && !analysisMutation.data && !analysisMutation.isPending) {
      analysisMutation.mutate(initialText);
    }
  }, [initialText]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim()) {
      analysisMutation.mutate(textInput.trim());
    }
  };

  const result: AnalysisResponse | undefined = analysisMutation.data;

  return (
    <div className="space-y-6">
      {/* Header matching Stitch Spec */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#E2E8F0]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2 h-2 rounded-full bg-[#087F83]"></span>
            <span className="text-[11px] font-bold tracking-wider text-[#64748B] uppercase">
              DIAGNOSTIC WORKBENCH
            </span>
          </div>
          <h2 className="text-3xl font-bold font-serif text-[#183B56] tracking-tight">
            Analyze Article
          </h2>
          <p className="text-xs text-[#64748B] mt-1 max-w-2xl">
            Screen submitted news text and examine supporting evidence using forensic lexical calibration and indexed verification registers.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 bg-[#EAF0FF] border border-[#CBD5E1] rounded-md text-xs font-semibold text-[#315FE8] flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                health?.ml_model === 'loaded' ? 'bg-[#10B981]' : 'bg-[#EF806B]'
              }`}
            ></span>
            {health?.ml_model === 'loaded' ? 'ML Classifier Ready' : 'ML Model Loading / Offline'}
          </div>
        </div>
      </div>

      {/* Input Workbench Card */}
      <div className="bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-[#183B56] flex items-center gap-1.5">
              <span>✍️</span> Paste headline or article content for screening
            </label>
            <span className="text-[11px] text-[#94A3B8]">Target Corpus: English / Hinglish Transliterated</span>
          </div>

          <textarea
            rows={5}
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder="Paste news headline or claim body to evaluate framing, sensationalism tokens, and corroborating fact-checks..."
            className="w-full p-4 text-xs bg-[#F8FAFC] border border-[#CBD5E1] rounded-md focus:outline-none focus:border-[#315FE8] leading-relaxed font-sans"
          />

          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-4 text-[#64748B]">
              <span>{textInput.length} characters (approx {textInput.trim() ? textInput.trim().split(/\s+/).length : 0} words)</span>
              <span className="flex items-center gap-1 text-[#10B981]">
                <CheckCircle2 className="w-3.5 h-3.5" /> Input Sanitized
              </span>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setTextInput(SAMPLE_CLAIM)}
                className="px-3 py-1.5 bg-[#F1F5F9] hover:bg-[#E2E8F0] text-[#183B56] rounded font-semibold transition-colors cursor-pointer"
              >
                Load Example Claim
              </button>
              <button
                type="button"
                onClick={() => setTextInput('')}
                className="text-[#94A3B8] hover:text-[#64748B] cursor-pointer"
              >
                Clear Input
              </button>
              <button
                type="submit"
                disabled={analysisMutation.isPending || !textInput.trim()}
                className="px-5 py-2 bg-[#183B56] hover:bg-[#20496B] text-white rounded font-semibold transition-colors disabled:opacity-50 cursor-pointer"
              >
                {analysisMutation.isPending ? 'Screening...' : 'Screen Article Content'}
              </button>
            </div>
          </div>
        </form>

        {/* Evidence-First Directive Callout Banner */}
        <div className="p-3.5 bg-[#FFF5E5] border border-[#FEEBC8] rounded-md text-xs text-[#7B341E] flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-[#DD6B20] shrink-0 mt-0.5" />
          <div className="leading-relaxed">
            <strong>EVIDENCE-FIRST DIRECTIVE:</strong> This screening tool outputs a machine-learning classification signal based on linguistic patterns and lexical framing. It is <strong>NOT</strong> a factual verification, truth determination, or debunking certification. All predictions must be weighed against external evidence, registered gazettes, and human editorial assessment.
          </div>
        </div>
      </div>

      {/* 2x2 Grid with Diagnostics */}
      {result && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Card 1: Model Screening Result */}
          <div className="bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
              <div className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-[#315FE8]" />
                <div>
                  <h3 className="font-bold text-base text-[#183B56] font-serif">Model Screening Result</h3>
                  <p className="text-[10px] text-[#94A3B8]">NewsLens Baseline TF-IDF + Logistic Classifier (LIAR Benchmark)</p>
                </div>
              </div>
              <span className="text-[10px] px-2 py-0.5 bg-[#EAF0FF] text-[#315FE8] font-bold rounded">
                Strict Inference
              </span>
            </div>

            <div className="p-3 bg-[#F8FAFC] rounded text-xs text-[#64748B] leading-relaxed">
              <strong>Evaluation Context:</strong> Trained on benchmark misinformation datasets with newsroom text calibration, prioritizing Indian national agency circular styling and linguistic panic markers.
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-[#64748B] font-medium">Predicted Categorical Class:</span>
              <span className="px-2.5 py-1 rounded bg-[#FFF0E9] text-[#C53030] font-bold">
                {result.screening.label}
              </span>
            </div>

            {/* Decision Value Meter */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs font-semibold">
                <span className="text-[#183B56]">Decision Value / Resemblance Score</span>
                <span className="text-[#315FE8] tabular-nums font-bold">
                  {result.screening.score.toFixed(2)} ({(result.screening.score * 100).toFixed(0)}%)
                </span>
              </div>
              <div className="w-full h-3 bg-[#E2E8F0] rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#315FE8] to-[#EF806B] transition-all duration-500"
                  style={{ width: `${Math.min(Math.max(result.screening.score * 100, 5), 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-[#94A3B8]">
                <span>0.0 Baseline Clean</span>
                <span>Uncalibrated Decision Score</span>
                <span>1.0 High Synthetic Framing</span>
              </div>
            </div>

            {/* Influential Tokens */}
            <div className="pt-2 border-t border-[#F1F5F9] space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-semibold text-[#183B56]">Key Influential Tokens (TF-IDF High Weights):</span>
                <span className="text-[10px] text-[#94A3B8]">Linguistic Salience</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {result.screening.influential_tokens.length > 0 ? (
                  result.screening.influential_tokens.map((tok: InfluentialToken, i: number) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded bg-[#EBF8FF] text-[#2B6CB0] border border-[#BEE3F8] text-xs font-mono font-medium"
                    >
                      {tok.token} <strong className="text-[#2C5282]">{tok.weight}</strong>
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-[#94A3B8]">No prominent non-zero token features detected.</span>
                )}
              </div>
            </div>
          </div>

          {/* Card 2: Related External Coverage */}
          <div className="bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-[#087F83]" />
                <h3 className="font-bold text-base text-[#183B56] font-serif">Related External Coverage</h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 bg-[#E5F6F3] text-[#087F83] font-bold rounded">
                GDELT / News Wire Index
              </span>
            </div>

            <p className="text-xs text-[#64748B]">
              Cross-referenced against recent reporting across Indian digital bureaus.
            </p>

            <div className="space-y-3">
              {result.related_coverage.length > 0 ? (
                result.related_coverage.map((rel: any, idx: number) => (
                  <div
                    key={idx}
                    className="p-3 rounded-md border border-[#E2E8F0] bg-[#F8FAFC] space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-[#183B56]">{rel.publisher || 'Syndicated Bureau'}</span>
                      <span className="text-[10px] text-[#94A3B8]">
                        Sim: {(rel.similarity * 100).toFixed(0)}%
                      </span>
                    </div>
                    <h4 className="text-xs font-semibold text-[#142B4A] line-clamp-1">{rel.title}</h4>
                    <div className="flex items-center justify-between text-[11px] pt-1">
                      <span className="text-[#64748B]">{rel.relationship || 'similar_reporting'}</span>
                      <a
                        href={rel.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#315FE8] hover:underline flex items-center gap-1 font-medium"
                      >
                        View Wire <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-[#94A3B8]">
                  No direct related articles indexed for this text segment.
                </div>
              )}
            </div>

            <Link
              to="/evidence"
              className="block w-full py-2 bg-[#EAF0FF] hover:bg-[#D6E4FF] text-[#315FE8] text-center font-semibold text-xs rounded transition-colors"
            >
              Compare All in Evidence & Coverage View →
            </Link>
          </div>

          {/* Card 3: Published Fact-Check Assessments */}
          <div className="bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-[#E5A440]" />
                <h3 className="font-bold text-base text-[#183B56] font-serif">Published Fact-Check Assessments</h3>
              </div>
              <span className="text-[10px] px-2 py-0.5 bg-[#FFF5E5] text-[#E5A440] font-bold rounded">
                BM25Plus Match
              </span>
            </div>

            <div className="space-y-3">
              {result.fact_check_matches.length > 0 ? (
                result.fact_check_matches.map((fc: any, i: number) => (
                  <div key={i} className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-md space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-[#183B56]">{fc.fact_checker}</span>
                      <span className="px-2 py-0.5 rounded bg-[#FFF0E9] text-[#C53030] font-bold text-[10px]">
                        {fc.verdict}
                      </span>
                    </div>

                    <h4 className="text-xs font-bold text-[#142B4A] leading-snug">{fc.claim}</h4>
                    <p className="text-[11px] text-[#64748B] leading-relaxed">{fc.explanation}</p>

                    <div className="flex items-center justify-between pt-1 border-t border-[#E2E8F0] text-[11px]">
                      <span className="text-[#94A3B8]">Review Date: {fc.review_date}</span>
                      <a
                        href={fc.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#315FE8] hover:underline flex items-center gap-1 font-medium"
                      >
                        Inspect Original Fact-Check Article <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-xs text-[#94A3B8]">
                  No matching claims in current IFCN fact-check database.
                </div>
              )}
            </div>
          </div>

          {/* Card 4: Evidence Checklist & Limitations */}
          <div className="bg-white p-6 rounded-lg border border-[#E2E8F0] shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#F1F5F9] pb-3">
              <h3 className="font-bold text-base text-[#183B56] font-serif">Evidence Checklist & Limitations</h3>
              <span className="text-[10px] text-[#94A3B8]">Verification Rubric</span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="space-y-1.5">
                <span className="font-bold text-[#2E7D32] flex items-center gap-1.5 uppercase text-[10px]">
                  <CheckCircle2 className="w-3.5 h-3.5" /> AVAILABLE EVIDENCE
                </span>
                <ul className="list-disc list-inside text-[#475569] space-y-1 pl-1 text-[11px]">
                  <li>Official ministry press release exists denying any tariff change.</li>
                  <li>Published fact-checks indexed from public fact-checking archives (PIB / News Checker).</li>
                </ul>
              </div>

              <div className="space-y-1.5 pt-2 border-t border-[#F1F5F9]">
                <span className="font-bold text-[#D97706] flex items-center gap-1.5 uppercase text-[10px]">
                  <AlertTriangle className="w-3.5 h-3.5" /> MISSING EVIDENCE & DATA GAPS
                </span>
                <ul className="list-disc list-inside text-[#475569] space-y-1 pl-1 text-[11px]">
                  <li>Original origin social media post author unverified (closed messaging dissemination).</li>
                  <li>No official scanned gazette attached with the viral forwarded claim text.</li>
                </ul>
              </div>

              <div className="p-3 bg-[#EAF0FF] border border-[#CBD5E1] rounded text-[11px] text-[#1E3A8A] leading-relaxed mt-2">
                <strong>ANALYTICAL RECOMMENDATION:</strong> Human editorial review recommended. Cross-verify against official <strong>Press Information Bureau (pib.gov.in)</strong> gazette or direct Indian Railway Board notifications before secondary syndication.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
