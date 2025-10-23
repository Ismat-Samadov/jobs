'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';

// Force dynamic rendering to prevent build-time errors
export const dynamic = 'force-dynamic';

interface AnalyticsData {
  overview: {
    totalLeads: number;
    todayLeads: number;
    avgDailyLeads: number;
    growthPercentage: string;
    uniquePhones: number;
    duplicateRate: string;
    dataQualityPercentage: string;
  };
  leadsBySource: { website: string; count: string }[];
  topSources: { website: string; count: string }[];
  leadsByDate: { date: string; count: string }[];
  leadsLast30Days: { date: string; count: string }[];
  dataQuality: { data_status: string; count: string }[];
  hourlyDistribution: { hour: string; count: string }[];
  weekdayDistribution: { day_name: string; day_num: string; count: string }[];
  dailyGrowth: { date: string; count: string; growth: string }[];
}

// Helper function to get gradient colors for sources
function getSourceColor(index: number): string {
  const gradients = [
    'from-blue-500 to-blue-600',
    'from-purple-500 to-purple-600',
    'from-green-500 to-green-600',
    'from-orange-500 to-orange-600',
    'from-pink-500 to-pink-600',
    'from-indigo-500 to-indigo-600',
    'from-red-500 to-red-600',
    'from-teal-500 to-teal-600',
    'from-cyan-500 to-cyan-600',
    'from-yellow-500 to-yellow-600',
  ];
  return gradients[index % gradients.length];
}

function getBadgeColor(website: string): string {
  const colors: { [key: string]: string } = {
    'evv.az': 'bg-blue-100 text-blue-800',
    'villa.az': 'bg-purple-100 text-purple-800',
    'bul.az': 'bg-green-100 text-green-800',
    'repetitor.az': 'bg-pink-100 text-pink-800',
  };

  if (colors[website]) {
    return colors[website];
  }

  const colorVariants = [
    'bg-indigo-100 text-indigo-800',
    'bg-yellow-100 text-yellow-800',
    'bg-red-100 text-red-800',
    'bg-teal-100 text-teal-800',
    'bg-orange-100 text-orange-800',
    'bg-cyan-100 text-cyan-800',
  ];

  const hash = website.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colorVariants[hash % colorVariants.length];
}

export default function AnalyticsPage() {
  const sessionData = useSession();
  const session = sessionData?.data;
  const status = sessionData?.status;
  const router = useRouter();
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/login');
    }
  }, [status, router]);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await fetch('/api/analytics');
      const data = await response.json();
      setAnalytics(data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !analytics) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-xl font-semibold text-gray-700">Loading Analytics...</div>
      </div>
    );
  }

  const maxLeadCount = Math.max(...analytics.leadsBySource.map(s => parseInt(s.count)));

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      {/* Navigation Header */}
      <div className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 shadow-lg">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <h1 className="text-lg sm:text-xl font-bold text-white">Analytics Dashboard</h1>
                <p className="text-xs text-white/80 hidden sm:block">Comprehensive Data Insights</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <a
                href="/dashboard"
                className="inline-flex items-center space-x-2 px-4 py-2 bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white text-sm font-medium rounded-lg transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                </svg>
                <span>Dashboard</span>
              </a>
              {session?.user?.role === 'admin' && (
                <a
                  href="/admin"
                  className="inline-flex items-center space-x-2 px-4 py-2 bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white text-sm font-medium rounded-lg transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>Admin</span>
                </a>
              )}
              <a
                href="/api/auth/signout"
                className="inline-flex items-center space-x-2 px-4 py-2 bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white text-sm font-medium rounded-lg transition-all"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span>Logout</span>
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-6 sm:py-8">
        {/* Overview Cards */}
        <div className="grid grid-cols-1 gap-4 sm:gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-6 sm:mb-8">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 overflow-hidden shadow-xl rounded-2xl transform hover:scale-105 transition-all duration-300">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-blue-100 uppercase tracking-wide">
                    Total Leads
                  </dt>
                  <dd className="mt-2 text-4xl font-extrabold text-white">
                    {analytics.overview.totalLeads.toLocaleString()}
                  </dd>
                </div>
                <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-500 to-green-600 overflow-hidden shadow-xl rounded-2xl transform hover:scale-105 transition-all duration-300">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-green-100 uppercase tracking-wide">
                    Today's Leads
                  </dt>
                  <dd className="mt-2 text-4xl font-extrabold text-white">
                    {analytics.overview.todayLeads.toLocaleString()}
                  </dd>
                </div>
                <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-500 to-purple-600 overflow-hidden shadow-xl rounded-2xl transform hover:scale-105 transition-all duration-300">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-purple-100 uppercase tracking-wide">
                    Unique Contacts
                  </dt>
                  <dd className="mt-2 text-4xl font-extrabold text-white">
                    {analytics.overview.uniquePhones.toLocaleString()}
                  </dd>
                  <p className="text-xs text-purple-100 mt-1">{analytics.overview.duplicateRate}% duplicates</p>
                </div>
                <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-orange-500 to-orange-600 overflow-hidden shadow-xl rounded-2xl transform hover:scale-105 transition-all duration-300">
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <dt className="text-sm font-medium text-orange-100 uppercase tracking-wide">
                    Data Quality
                  </dt>
                  <dd className="mt-2 text-4xl font-extrabold text-white">
                    {analytics.overview.dataQualityPercentage}%
                  </dd>
                  <p className="text-xs text-orange-100 mt-1">Complete Data</p>
                </div>
                <div className="bg-white/20 backdrop-blur-sm rounded-xl p-3">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Leads by Source */}
          <div className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100">
            <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-blue-50 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 flex items-center">
                <div className="bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg p-2 mr-3">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                Leads by Source
              </h2>
            </div>
            <div className="p-6 space-y-4 max-h-96 overflow-y-auto">
              {analytics.leadsBySource.map((source, index) => {
                const percentage = (parseInt(source.count) / analytics.overview.totalLeads * 100).toFixed(1);
                return (
                  <div key={source.website} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${getBadgeColor(source.website)}`}>
                        {source.website}
                      </span>
                      <span className="text-sm font-bold text-gray-900">
                        {parseInt(source.count).toLocaleString()} ({percentage}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${getSourceColor(index)} transition-all duration-500`}
                        style={{ width: `${percentage}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Top 5 Sources */}
          <div className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100">
            <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-purple-50 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 flex items-center">
                <div className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg p-2 mr-3">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                  </svg>
                </div>
                Top 5 Sources
              </h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {analytics.topSources.map((source, index) => (
                  <div key={source.website} className="flex items-center space-x-4">
                    <div className={`flex-shrink-0 w-10 h-10 rounded-full bg-gradient-to-r ${getSourceColor(index)} flex items-center justify-center text-white font-bold text-lg`}>
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-semibold text-gray-900">{source.website}</span>
                        <span className="text-sm font-bold text-gray-600">{parseInt(source.count).toLocaleString()}</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-full bg-gradient-to-r ${getSourceColor(index)} rounded-full transition-all duration-500`}
                          style={{ width: `${(parseInt(source.count) / parseInt(analytics.topSources[0].count) * 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Data Quality and Collection Patterns */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Data Quality Breakdown */}
          <div className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100">
            <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-green-50 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 flex items-center">
                <div className="bg-gradient-to-r from-green-500 to-teal-500 rounded-lg p-2 mr-3">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                Data Quality Breakdown
              </h2>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                {analytics.dataQuality.map((status) => {
                  const percentage = (parseInt(status.count) / analytics.overview.totalLeads * 100).toFixed(1);
                  const isComplete = status.data_status === 'Complete Data';
                  return (
                    <div key={status.data_status} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <span className={`flex-shrink-0 w-10 h-10 rounded-lg ${isComplete ? 'bg-gradient-to-r from-green-400 to-teal-400' : 'bg-gradient-to-r from-gray-400 to-gray-500'} flex items-center justify-center text-white`}>
                            {isComplete ? (
                              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                              </svg>
                            )}
                          </span>
                          <span className="text-sm font-semibold text-gray-900">{status.data_status}</span>
                        </div>
                        <span className="text-sm font-bold text-gray-600">
                          {parseInt(status.count).toLocaleString()} ({percentage}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${isComplete ? 'bg-gradient-to-r from-green-400 to-teal-400' : 'bg-gradient-to-r from-gray-400 to-gray-500'}`}
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Hourly Collection Pattern */}
          <div className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100">
            <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-blue-50 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900 flex items-center">
                <div className="bg-gradient-to-r from-blue-500 to-indigo-500 rounded-lg p-2 mr-3">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                Collection Time Pattern
              </h2>
            </div>
            <div className="p-6">
              <div className="flex items-end justify-between space-x-1 h-48">
                {analytics.hourlyDistribution.map((hour) => {
                  const maxCount = Math.max(...analytics.hourlyDistribution.map(h => parseInt(h.count)));
                  const height = maxCount > 0 ? (parseInt(hour.count) / maxCount * 100) : 0;
                  const hourNum = parseInt(hour.hour);
                  return (
                    <div key={hour.hour} className="flex-1 flex flex-col items-center group">
                      <div
                        className="w-full bg-gradient-to-t from-blue-500 to-blue-300 rounded-t hover:from-blue-600 hover:to-blue-400 transition-all cursor-pointer relative"
                        style={{ height: `${height}%`, minHeight: '4px' }}
                        title={`${hourNum}:00 - ${parseInt(hour.count).toLocaleString()} leads`}
                      >
                        <span className="absolute -top-8 left-1/2 transform -translate-x-1/2 text-xs font-semibold text-gray-700 opacity-0 group-hover:opacity-100 transition-opacity bg-white px-2 py-1 rounded shadow-lg whitespace-nowrap z-10">
                          {parseInt(hour.count).toLocaleString()}
                        </span>
                      </div>
                      {hourNum % 3 === 0 && (
                        <span className="text-xs text-gray-500 mt-2">{hourNum}</span>
                      )}
                    </div>
                  );
                })}
              </div>
              <div className="mt-2 text-center text-xs text-gray-500">Hours (24h format)</div>
            </div>
          </div>
        </div>

        {/* Weekly Pattern */}
        <div className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100 mb-6">
          <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-purple-50 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900 flex items-center">
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg p-2 mr-3">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              Weekly Collection Pattern
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-7 gap-3">
              {analytics.weekdayDistribution.map((day) => {
                const maxCount = Math.max(...analytics.weekdayDistribution.map(d => parseInt(d.count)));
                const percentage = maxCount > 0 ? (parseInt(day.count) / maxCount * 100) : 0;
                const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
                return (
                  <div key={day.day_name} className="text-center">
                    <div className="mb-2 text-xs font-semibold text-gray-700">{dayNames[parseInt(day.day_num)]}</div>
                    <div className="bg-gray-100 rounded-lg p-3 hover:bg-gray-200 transition-colors">
                      <div className="text-2xl font-bold text-gray-900">{parseInt(day.count).toLocaleString()}</div>
                      <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-500"
                          style={{ width: `${percentage}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Last 30 Days Chart */}
        <div className="bg-white shadow-xl rounded-2xl overflow-hidden border border-gray-100">
          <div className="px-6 py-4 bg-gradient-to-r from-gray-50 to-indigo-50 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900 flex items-center">
              <div className="bg-gradient-to-r from-indigo-500 to-purple-500 rounded-lg p-2 mr-3">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                </svg>
              </div>
              Leads Trend (Last 30 Days)
            </h2>
          </div>
          <div className="p-6">
            <div className="flex items-end justify-between space-x-2 h-64">
              {analytics.leadsLast30Days.slice(-30).map((day) => {
                const maxCount = Math.max(...analytics.leadsLast30Days.map(d => parseInt(d.count)));
                const height = maxCount > 0 ? (parseInt(day.count) / maxCount * 100) : 0;
                const date = new Date(day.date);

                return (
                  <div key={day.date} className="flex-1 flex flex-col items-center group">
                    <div className="relative w-full">
                      <div
                        className="w-full bg-gradient-to-t from-blue-500 to-blue-300 rounded-t-lg hover:from-blue-600 hover:to-blue-400 transition-all cursor-pointer"
                        style={{ height: `${height * 2}px`, minHeight: '4px' }}
                        title={`${date.toLocaleDateString()}: ${parseInt(day.count).toLocaleString()} leads`}
                      >
                        <span className="absolute -top-6 left-1/2 transform -translate-x-1/2 text-xs font-semibold text-gray-700 opacity-0 group-hover:opacity-100 transition-opacity bg-white px-2 py-1 rounded shadow-lg whitespace-nowrap">
                          {parseInt(day.count).toLocaleString()}
                        </span>
                      </div>
                    </div>
                    {date.getDate() % 5 === 0 && (
                      <span className="text-xs text-gray-500 mt-2 transform rotate-0">
                        {date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
