import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Plug,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  KeyRound,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  Globe,
  Radio,
  ShieldCheck,
  Building2,
  Search,
} from 'lucide-react';
import { newsApi } from '../services/api';
import type { ProviderStatusItem } from '../types/api';

export const IntegrationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [copied, setCopied] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [testResults, setTestResults] = useState<Record<string, { status: string; message: string; success: boolean }>>({});
  const [activeRefreshProvider, setActiveRefreshProvider] = useState<string | null>(null);

  const { data: overview, isLoading, error, refetch } = useQuery({
    queryKey: ['integrations-overview'],
    queryFn: newsApi.getIntegrationsOverview,
    refetchInterval: 15000,
  });

  const testMutation = useMutation({
    mutationFn: (providerId: string) => newsApi.testProviderConnection(providerId),
    onSuccess: (data, providerId) => {
      setTestResults((prev) => ({
        ...prev,
        [providerId]: {
          status: data.status,
          message: data.message,
          success: data.success,
        },
      }));
      queryClient.invalidateQueries({ queryKey: ['integrations-overview'] });
    },
    onError: (err: any, providerId) => {
      setTestResults((prev) => ({
        ...prev,
        [providerId]: {
          status: 'error',
          message: err?.response?.data?.message || err?.message || 'Connection test failed',
          success: false,
        },
      }));
    },
  });

  const refreshMutation = useMutation({
    mutationFn: ({ providerId, profile }: { providerId: string; profile?: string }) =>
      newsApi.refreshProvider(providerId, { profile, max_pages: 1 }),
    onMutate: ({ providerId }) => {
      setActiveRefreshProvider(providerId);
    },
    onSettled: () => {
      setActiveRefreshProvider(null);
      queryClient.invalidateQueries({ queryKey: ['integrations-overview'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['articles'] });
    },
  });

  const handleCopyEnvTemplate = () => {
    const template = `# NewsLens India Provider Credentials
NEWSDATA_ENABLED=true
NEWSDATA_API_KEY=your_newsdata_key_here

CURRENTS_ENABLED=true
CURRENTS_API_KEY=your_currents_key_here

GOOGLE_FACTCHECK_ENABLED=true
GOOGLE_FACTCHECK_API_KEY=your_google_cloud_key_here

GUARDIAN_ENABLED=true
GUARDIAN_API_KEY=your_guardian_key_here

PIB_ENABLED=true
ABP_RSS_ENABLED=true
AMAR_UJALA_RSS_ENABLED=true`;

    navigator.clipboard.writeText(template);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  if (isLoading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[60vh]">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 text-[#315FE8] animate-spin" />
          <p className="text-sm font-medium text-[#64748B]">Loading provider integration registry...</p>
        </div>
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-red-800 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 shrink-0" />
          <div>
            <h3 className="text-sm font-semibold">Failed to load integrations</h3>
            <p className="text-xs mt-1 text-red-700">Unable to communicate with the central integration manager.</p>
            <button
              onClick={() => refetch()}
              className="mt-3 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-medium"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const providers = overview.providers || [];
  const categories = ['all', ...Array.from(new Set(providers.map((p) => p.category)))];
  const filteredProviders =
    selectedCategory === 'all' ? providers : providers.filter((p) => p.category === selectedCategory);

  const getStatusBadge = (provider: ProviderStatusItem) => {
    switch (provider.status_label) {
      case 'operational':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Operational
          </span>
        );
      case 'configured_not_tested':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <Check className="w-3 h-3 text-blue-600" /> Configured
          </span>
        );
      case 'not_configured':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
            <KeyRound className="w-3 h-3 text-amber-600" /> Needs API Key
          </span>
        );
      case 'rate_limited':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-50 text-orange-700 border border-orange-200">
            <Clock className="w-3 h-3 text-orange-600" /> Rate Limited
          </span>
        );
      case 'disabled':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
            Disabled
          </span>
        );
      case 'retired':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-500 border border-gray-200">
            Retired
          </span>
        );
      case 'backlog':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
            Backlog
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-200">
            <XCircle className="w-3 h-3 text-red-600" /> Error
          </span>
        );
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'Global Aggregator':
        return <Globe className="w-4 h-4 text-[#315FE8]" />;
      case 'Fact-Check Evidence':
        return <ShieldCheck className="w-4 h-4 text-emerald-600" />;
      case 'Official Government':
        return <Building2 className="w-4 h-4 text-amber-600" />;
      case 'Search/Discovery':
        return <Search className="w-4 h-4 text-purple-600" />;
      default:
        return <Radio className="w-4 h-4 text-blue-500" />;
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Title & Mission Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-gray-200 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <Plug className="w-6 h-6 text-[#315FE8]" />
            <h1 className="text-2xl font-bold tracking-tight text-[#142B4A]">API Integration Manager</h1>
          </div>
          <p className="text-sm text-[#64748B] mt-1">
            Centralized credentials configuration, multi-provider health checks, and quota governance.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-white border border-gray-300 hover:bg-gray-50 text-[#1E293B] rounded-lg text-xs font-medium shadow-sm transition"
          >
            <RefreshCw className="w-3.5 h-3.5 text-[#64748B]" />
            Refresh Telemetry
          </button>
          <button
            onClick={handleCopyEnvTemplate}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-[#142B4A] hover:bg-[#1E3A5F] text-white rounded-lg text-xs font-medium shadow-sm transition"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'Template Copied!' : 'Copy .env Template'}
          </button>
        </div>
      </div>

      {/* Summary KPI Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-medium text-[#64748B]">Registered Providers</div>
          <div className="text-2xl font-bold text-[#142B4A] mt-1">{overview.total_registered}</div>
          <div className="text-[11px] text-[#94A3B8] mt-0.5">Canonical registry total</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-medium text-[#64748B]">Configured & Active</div>
          <div className="text-2xl font-bold text-blue-600 mt-1">{overview.configured_count}</div>
          <div className="text-[11px] text-[#94A3B8] mt-0.5">Credentials or feeds present</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-medium text-[#64748B]">Operational</div>
          <div className="text-2xl font-bold text-emerald-600 mt-1">{overview.operational_count}</div>
          <div className="text-[11px] text-[#94A3B8] mt-0.5">Successful sync verified</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-medium text-[#64748B]">Awaiting Credentials</div>
          <div className="text-2xl font-bold text-amber-600 mt-1">{overview.awaiting_credentials_count}</div>
          <div className="text-[11px] text-[#94A3B8] mt-0.5">Requires API key in .env</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
          <div className="text-xs font-medium text-[#64748B]">Disabled / Inactive</div>
          <div className="text-2xl font-bold text-gray-500 mt-1">{overview.disabled_count}</div>
          <div className="text-[11px] text-[#94A3B8] mt-0.5">Turned off in settings</div>
        </div>
      </div>

      {/* Central Credentials Notice Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 text-sm text-blue-900 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <KeyRound className="w-5 h-5 text-[#315FE8] shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-[#142B4A]">Centralized Credentials Architecture</h4>
            <p className="text-xs text-blue-800 mt-0.5 leading-relaxed">
              To activate an external API provider, paste its API key into your root <code className="bg-blue-100 px-1 py-0.5 rounded text-blue-900 font-mono">.env</code> file and restart NewsLens India. No Python source code edits are required. Secrets are strictly managed in the backend and never exposed to the browser.
            </p>
          </div>
        </div>
        <div className="shrink-0 text-right">
          <button
            onClick={handleCopyEnvTemplate}
            className="text-xs font-semibold text-[#315FE8] hover:text-[#1E3A5F] underline"
          >
            View example .env format
          </button>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-200 pb-3 overflow-x-auto">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setSelectedCategory(cat)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition shrink-0 ${
              selectedCategory === cat
                ? 'bg-[#142B4A] text-white shadow-sm'
                : 'bg-white border border-gray-200 text-[#64748B] hover:bg-gray-50'
            }`}
          >
            {cat === 'all' ? 'All Providers' : cat}
          </button>
        ))}
      </div>

      {/* Providers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProviders.map((provider) => {
          const testRes = testResults[provider.id];
          const isTesting = testMutation.isPending && testMutation.variables === provider.id;
          const isRefreshing = activeRefreshProvider === provider.id;

          return (
            <div
              key={provider.id}
              className="bg-white rounded-xl border border-gray-200 shadow-sm hover:shadow-md transition flex flex-col justify-between overflow-hidden"
            >
              <div className="p-5 space-y-4">
                {/* Header & Badges */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-gray-50 border border-gray-100">
                      {getCategoryIcon(provider.category)}
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm text-[#142B4A] leading-tight">{provider.name}</h3>
                      <p className="text-[11px] text-[#64748B] mt-0.5">{provider.domain}</p>
                    </div>
                  </div>
                  <div>{getStatusBadge(provider)}</div>
                </div>

                {/* Metadata Details */}
                <div className="space-y-1.5 pt-2 border-t border-gray-100 text-xs">
                  <div className="flex items-center justify-between text-[#64748B]">
                    <span>Category:</span>
                    <span className="font-medium text-[#1E293B]">{provider.category}</span>
                  </div>
                  <div className="flex items-center justify-between text-[#64748B]">
                    <span>Ingestion Type:</span>
                    <span className="font-mono text-[11px] uppercase bg-gray-100 px-1.5 py-0.2 rounded text-gray-700">
                      {provider.source_type}
                    </span>
                  </div>
                  {provider.requires_api_key && (
                    <div className="flex items-center justify-between text-[#64748B]">
                      <span>Key Variable:</span>
                      <code className="text-[11px] text-[#315FE8] font-mono bg-blue-50 px-1 py-0.5 rounded">
                        {provider.env_key_name || 'N/A'}
                      </code>
                    </div>
                  )}
                  {provider.last_refresh_at && (
                    <div className="flex items-center justify-between text-[#64748B]">
                      <span>Last Ingest:</span>
                      <span className="font-medium text-[#1E293B]">
                        {new Date(provider.last_refresh_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  )}
                  {provider.items_count > 0 && (
                    <div className="flex items-center justify-between text-[#64748B]">
                      <span>Articles Indexed:</span>
                      <span className="font-medium text-emerald-700">{provider.items_count} items</span>
                    </div>
                  )}
                  {provider.quota && (
                    <div className="flex items-center justify-between text-[#64748B]">
                      <span>Daily Quota:</span>
                      <span className="font-medium text-[#1E293B]">
                        {provider.quota.daily_consumed} / {provider.quota.daily_limit || '∞'} used
                      </span>
                    </div>
                  )}
                </div>

                {/* Connection Test Diagnostic Feedback */}
                {testRes && (
                  <div
                    className={`p-3 rounded-lg text-xs border ${
                      testRes.success
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                        : 'bg-red-50 border-red-200 text-red-800'
                    }`}
                  >
                    <div className="font-semibold flex items-center gap-1.5">
                      {testRes.success ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <XCircle className="w-3.5 h-3.5 text-red-600" />}
                      {testRes.success ? 'Connectivity Verified' : 'Test Unsuccessful'}
                    </div>
                    <div className="mt-1 text-[11px] leading-relaxed">{testRes.message}</div>
                  </div>
                )}
              </div>

                {/* Action Footer */}
              <div className="p-4 bg-gray-50 border-t border-gray-100 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  {provider.documentation_url && (
                    <a
                      href={provider.documentation_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#64748B] hover:text-[#315FE8] p-1.5 rounded hover:bg-gray-100 transition"
                      title="Documentation & Terms"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {provider.is_active && (
                    <>
                      <button
                        onClick={() => testMutation.mutate(provider.id)}
                        disabled={isTesting || !provider.is_configured}
                        className="px-2.5 py-1.5 bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 text-[#1E293B] rounded text-xs font-medium shadow-sm transition flex items-center gap-1.5"
                      >
                        {isTesting ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3 text-[#64748B]" />}
                        Test
                      </button>

                      <button
                        onClick={() =>
                          refreshMutation.mutate({
                            providerId: provider.id,
                            profile: provider.supported_profiles?.[0] || 'default',
                          })
                        }
                        disabled={isRefreshing || !provider.is_configured}
                        className="px-2.5 py-1.5 bg-[#315FE8] hover:bg-[#2548B8] disabled:opacity-50 text-white rounded text-xs font-medium shadow-sm transition flex items-center gap-1.5"
                      >
                        <RefreshCw className={`w-3 h-3 ${isRefreshing ? 'animate-spin' : ''}`} />
                        Sync Now
                      </button>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default IntegrationsPage;
