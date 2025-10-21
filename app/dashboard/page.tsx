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

// Property Card Component
function PropertyCard({ lead }: { lead: Lead }) {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const fullData = lead.full_data;
  const images = fullData?.images || [];
  const hasImages = images.length > 0;

  const nextImage = () => {
    setCurrentImageIndex((prev) => (prev + 1) % images.length);
  };

  const prevImage = () => {
    setCurrentImageIndex((prev) => (prev - 1 + images.length) % images.length);
  };

  // Format property details for display
  const getPropertyDetailLabel = (key: string): string => {
    const labels: { [key: string]: string } = {
      city: 'City',
      property_type: 'Property Type',
      location: 'Location',
      document: 'Document',
      floor: 'Floor',
      area: 'Area',
      area_sqm: 'Area (m²)',
      area_sot: 'Area (sot)',
      rooms: 'Rooms',
      mortgage: 'Mortgage',
      repair: 'Repair',
      country: 'Country',
      category: 'Category',
    };
    return labels[key] || key.charAt(0).toUpperCase() + key.slice(1);
  };

  return (
    <div className="bg-white rounded-xl shadow-lg overflow-hidden hover:shadow-xl transition-shadow duration-300">
      {/* Image Gallery */}
      {hasImages ? (
        <div className="relative h-64 bg-gray-200 group">
          <img
            src={images[currentImageIndex]}
            alt={fullData?.title || 'Property'}
            className="w-full h-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src = 'https://via.placeholder.com/400x300?text=No+Image';
            }}
          />

          {/* Image Navigation */}
          {images.length > 1 && (
            <>
              <button
                onClick={prevImage}
                className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Previous image"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <button
                onClick={nextImage}
                className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label="Next image"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>

              {/* Image Counter */}
              <div className="absolute bottom-3 right-3 bg-black/70 text-white text-xs px-2 py-1 rounded-full">
                {currentImageIndex + 1} / {images.length}
              </div>
            </>
          )}

          {/* Website Badge */}
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-600 text-white shadow-lg">
              {lead.website}
            </span>
          </div>
        </div>
      ) : (
        <div className="relative h-64 bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
          <svg className="w-20 h-20 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-600 text-white shadow-lg">
              {lead.website}
            </span>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="p-5">
        {/* Price */}
        {fullData?.price && (
          <div className="mb-3">
            <div className="text-3xl font-bold text-gray-900">
              {fullData.price.amount?.toLocaleString()} {fullData.price.currency}
            </div>
          </div>
        )}

        {/* Title */}
        {fullData?.title && (
          <h3 className="text-lg font-semibold text-gray-800 mb-3 line-clamp-2 min-h-[3.5rem]">
            {fullData.title}
          </h3>
        )}

        {/* Address */}
        {fullData?.address && (
          <div className="flex items-start text-sm text-gray-600 mb-3">
            <svg className="w-4 h-4 mr-1 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="line-clamp-2">{fullData.address}</span>
          </div>
        )}

        {/* Property Details Grid */}
        {fullData?.property_details && Object.keys(fullData.property_details).length > 0 && (
          <div className="grid grid-cols-2 gap-3 mb-4 pb-4 border-b border-gray-200">
            {Object.entries(fullData.property_details).slice(0, 4).map(([key, value]) => (
              <div key={key} className="bg-gray-50 rounded-lg p-2">
                <div className="text-xs text-gray-500 mb-0.5">{getPropertyDetailLabel(key)}</div>
                <div className="text-sm font-semibold text-gray-900 truncate">{value}</div>
              </div>
            ))}
          </div>
        )}

        {/* Features */}
        {fullData?.features && fullData.features.length > 0 && (
          <div className="mb-4 pb-4 border-b border-gray-200">
            <div className="flex flex-wrap gap-1.5">
              {fullData.features.slice(0, 6).map((feature, index) => (
                <span
                  key={index}
                  className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-50 text-green-700 border border-green-200"
                >
                  {feature}
                </span>
              ))}
              {fullData.features.length > 6 && (
                <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-600">
                  +{fullData.features.length - 6} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* Contact Info */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <a
              href={`tel:${lead.phone_number}`}
              className="flex items-center text-blue-600 hover:text-blue-700 font-semibold"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              {lead.phone_number}
            </a>
          </div>

          {/* Source Link & Date */}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <a
              href={lead.source}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 flex items-center"
            >
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              View Original
            </a>
            <span>{new Date(lead.created_at).toLocaleDateString()}</span>
          </div>

          {/* Seller Info */}
          {fullData?.seller?.name && (
            <div className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2 mt-2">
              <span className="font-medium">Seller:</span> {fullData.seller.name}
              {fullData.seller.type && <span className="text-gray-500"> ({fullData.seller.type})</span>}
            </div>
          )}
        </div>
      </div>
    </div>
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

        {/* Property Leads Grid */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Recent Leads ({leads.length} results)
          </h2>

          {leads.length === 0 ? (
            <div className="bg-white shadow-lg rounded-xl p-12 text-center">
              <div className="flex flex-col items-center">
                <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-lg font-medium text-gray-500">No leads found</p>
                <p className="text-sm mt-1 text-gray-400">Try adjusting your filters</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {leads.map((lead) => (
                <PropertyCard key={lead.id} lead={lead} />
              ))}
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
