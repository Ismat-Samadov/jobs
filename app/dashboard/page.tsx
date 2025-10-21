'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';

interface Lead {
  id: number;
  phone_number: string;
  website: string;
  source: string;
  created_at: string;
  full_data?: {
    listing_type?: string;
    title?: string;
    price?: {
      amount?: number;
      currency?: string;
    };
    property_details?: {
      [key: string]: string;
    };
    description?: string;
    seller?: {
      name?: string;
      type?: string;
    };
    listing_info?: {
      ad_id?: string;
      views?: number;
      date_posted?: string;
    };
    images?: string[];
    features?: string[];
    address?: string;
  };
}

interface Stats {
  totalLeads: number;
  leadsToday: number;
  leadsThisWeek: number;
  leadsThisMonth: number;
  leadsBySource: { source: string; count: string }[];
  recentActivity: { date: string; count: string }[];
}

// Expandable Row Component
function LeadRow({ lead }: { lead: Lead }) {
  const [expanded, setExpanded] = useState(false);
  const fullData = lead.full_data;

  // Get a smart preview of the data
  const getDataPreview = () => {
    if (!fullData) return 'No data';

    // Try to create a meaningful preview from any data structure
    const parts = [];
    if (fullData.title) parts.push(fullData.title);
    if (fullData.price?.amount) parts.push(`${fullData.price.amount} ${fullData.price.currency || ''}`);

    if (parts.length > 0) return parts.join(' - ');

    // Fallback: count keys
    const keyCount = Object.keys(fullData).length;
    return `${keyCount} field${keyCount !== 1 ? 's' : ''}`;
  };

  // Render any data structure nicely
  const renderValue = (value: any, depth = 0): JSX.Element => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-gray-400">[]</span>;
      }
      return (
        <div className="space-y-1">
          {value.map((item, idx) => (
            <div key={idx} className="flex items-start">
              <span className="text-gray-400 mr-2">[{idx}]</span>
              <div className="flex-1">{renderValue(item, depth + 1)}</div>
            </div>
          ))}
        </div>
      );
    }

    if (typeof value === 'object') {
      return (
        <div className="space-y-1">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="flex items-start">
              <span className="text-gray-600 font-medium mr-2 min-w-[120px]">{k}:</span>
              <div className="flex-1 text-gray-900">{renderValue(v, depth + 1)}</div>
            </div>
          ))}
        </div>
      );
    }

    if (typeof value === 'string' && value.startsWith('http')) {
      return (
        <a href={value} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline break-all">
          {value}
        </a>
      );
    }

    return <span className="text-gray-900">{String(value)}</span>;
  };

  return (
    <>
      <tr
        className="hover:bg-blue-50 transition-colors cursor-pointer border-b border-gray-200"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3 whitespace-nowrap">
          <button className="text-gray-400 hover:text-gray-600 focus:outline-none">
            <svg
              className={`w-5 h-5 transition-transform ${expanded ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </td>
        <td className="px-4 py-3 whitespace-nowrap text-sm font-medium text-gray-900">
          #{lead.id}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <a
            href={`tel:${lead.phone_number}`}
            className="text-sm font-semibold text-blue-600 hover:text-blue-800 flex items-center"
            onClick={(e) => e.stopPropagation()}
          >
            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            {lead.phone_number}
          </a>
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
            lead.website === 'evv.az' ? 'bg-blue-100 text-blue-800' :
            lead.website === 'villa.az' ? 'bg-purple-100 text-purple-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {lead.website}
          </span>
        </td>
        <td className="px-4 py-3 text-sm text-gray-600 max-w-md truncate">
          {getDataPreview()}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          {fullData ? (
            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800">
              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Has Data
            </span>
          ) : (
            <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
              No Data
            </span>
          )}
        </td>
        <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600">
          {new Date(lead.created_at).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          })}
        </td>
      </tr>

      {/* Expanded Details Row */}
      {expanded && (
        <tr className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-blue-200">
          <td colSpan={7} className="px-6 py-6">
            <div className="space-y-4">
              {/* Source URL */}
              <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
                <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  Source URL
                </h4>
                <a
                  href={lead.source}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 hover:underline text-sm break-all"
                  onClick={(e) => e.stopPropagation()}
                >
                  {lead.source}
                </a>
              </div>

              {/* Full Data */}
              {fullData && (
                <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
                  <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                    <svg className="w-4 h-4 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Extracted Data
                  </h4>
                  <div className="bg-gray-50 rounded-md p-4 font-mono text-sm overflow-x-auto">
                    {renderValue(fullData)}
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function DashboardPage() {
  const { data: session } = useSession();
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [websiteFilter, setWebsiteFilter] = useState('all');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  useEffect(() => {
    fetchLeads();
    fetchStats();
  }, [page]);

  const fetchLeads = async () => {
    try {
      let url = `/api/leads?page=${page}&limit=20&search=${search}`;

      const response = await fetch(url);
      const data = await response.json();

      // Apply client-side filters
      let filteredData = data.data;

      if (websiteFilter !== 'all') {
        filteredData = filteredData.filter((lead: Lead) => lead.website === websiteFilter);
      }

      if (dateFrom) {
        filteredData = filteredData.filter((lead: Lead) =>
          new Date(lead.created_at) >= new Date(dateFrom)
        );
      }

      if (dateTo) {
        filteredData = filteredData.filter((lead: Lead) =>
          new Date(lead.created_at) <= new Date(dateTo)
        );
      }

      setLeads(filteredData);
      setTotalPages(data.pagination.totalPages);
    } catch (error) {
      console.error('Error fetching leads:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLeads();
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await fetch('/api/leads/export');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `leads_export_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error exporting:', error);
      alert('Failed to export leads');
    } finally {
      setExporting(false);
    }
  };

  const clearFilters = () => {
    setSearch('');
    setWebsiteFilter('all');
    setDateFrom('');
    setDateTo('');
    setPage(1);
    setTimeout(() => fetchLeads(), 100);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-xl font-semibold text-gray-700">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-6 sm:py-8">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-base sm:text-lg text-gray-600">
            Welcome back, <span className="font-semibold text-blue-600">{session?.user?.name}</span>
          </p>
        </div>

        {/* Statistics Cards */}
        {stats && (
          <div className="grid grid-cols-1 gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-6 sm:mb-8">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 overflow-hidden shadow-lg rounded-xl">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <dt className="text-sm font-medium text-blue-100 truncate">
                      Total Leads
                    </dt>
                    <dd className="mt-2 text-4xl font-bold text-white">
                      {stats.totalLeads.toLocaleString()}
                    </dd>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-green-500 to-green-600 overflow-hidden shadow-lg rounded-xl">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <dt className="text-sm font-medium text-green-100 truncate">
                      Today
                    </dt>
                    <dd className="mt-2 text-4xl font-bold text-white">
                      {stats.leadsToday.toLocaleString()}
                    </dd>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-purple-500 to-purple-600 overflow-hidden shadow-lg rounded-xl">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <dt className="text-sm font-medium text-purple-100 truncate">
                      This Week
                    </dt>
                    <dd className="mt-2 text-4xl font-bold text-white">
                      {stats.leadsThisWeek.toLocaleString()}
                    </dd>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-gradient-to-br from-orange-500 to-orange-600 overflow-hidden shadow-lg rounded-xl">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-1">
                    <dt className="text-sm font-medium text-orange-100 truncate">
                      This Month
                    </dt>
                    <dd className="mt-2 text-4xl font-bold text-white">
                      {stats.leadsThisMonth.toLocaleString()}
                    </dd>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Filters and Actions */}
        <div className="bg-white shadow-lg rounded-xl mb-6">
          <div className="px-4 sm:px-6 py-5">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Filters & Actions</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              {/* Search Input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Search
                </label>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Phone or source..."
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white"
                />
              </div>

              {/* Website Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Website
                </label>
                <select
                  value={websiteFilter}
                  onChange={(e) => setWebsiteFilter(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white"
                >
                  <option value="all">All Websites</option>
                  <option value="evv.az">EVV.AZ</option>
                  <option value="villa.az">Villa.AZ</option>
                </select>
              </div>

              {/* Date From */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  From Date
                </label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white"
                />
              </div>

              {/* Date To */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  To Date
                </label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-gray-900 bg-white"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row flex-wrap gap-3">
              <button
                onClick={handleSearch}
                className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-2.5 border border-transparent text-sm font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-sm"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Apply Filters
              </button>

              <button
                onClick={clearFilters}
                className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-2.5 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 shadow-sm"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Clear Filters
              </button>

              <button
                onClick={handleExport}
                disabled={exporting}
                className="w-full sm:w-auto inline-flex items-center justify-center px-6 py-2.5 border border-gray-300 text-sm font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {exporting ? 'Exporting...' : 'Export to Excel'}
              </button>
            </div>
          </div>
        </div>

        {/* Leads Data Table */}
        <div className="bg-white shadow-lg rounded-xl overflow-hidden mb-6">
          <div className="px-4 sm:px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">
              Leads Data ({leads.length} results)
            </h2>
          </div>

          {leads.length === 0 ? (
            <div className="p-12 text-center">
              <div className="flex flex-col items-center">
                <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg font-medium text-gray-500">No leads found</p>
                <p className="text-sm mt-1 text-gray-400">Try adjusting your filters</p>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gradient-to-r from-gray-50 to-gray-100">
                  <tr>
                    <th className="px-4 py-3 text-left w-12"></th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                      ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Phone Number
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Source
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Data Preview
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Created At
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white">
                  {leads.map((lead) => (
                    <LeadRow key={lead.id} lead={lead} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        <div className="bg-white shadow-lg rounded-xl px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => { setPage(Math.max(1, page - 1)); fetchLeads(); }}
                disabled={page === 1}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => { setPage(Math.min(totalPages, page + 1)); fetchLeads(); }}
                disabled={page === totalPages}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-gray-700">
                  Page <span className="font-bold text-blue-600">{page}</span> of{' '}
                  <span className="font-bold text-blue-600">{totalPages}</span>
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    onClick={() => { setPage(Math.max(1, page - 1)); fetchLeads(); }}
                    disabled={page === 1}
                    className="relative inline-flex items-center px-4 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => { setPage(Math.min(totalPages, page + 1)); fetchLeads(); }}
                    disabled={page === totalPages}
                    className="relative inline-flex items-center px-4 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Next
                  </button>
                </nav>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
