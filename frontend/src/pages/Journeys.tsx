import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { analyticsAPI } from '../utils/api';

const formatDuration = (seconds?: number | null) => {
  if (!seconds && seconds !== 0) return '—';
  const s = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};

// Helper to get date 7 days ago
const getDefaultStartDate = () => {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return date.toISOString().split('T')[0];
};

const getDefaultEndDate = () => {
  return new Date().toISOString().split('T')[0];
};

const Journeys: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [targetPathInput, setTargetPathInput] = useState('');
  const [targetPath, setTargetPath] = useState<string>('');
  const [withCapturedOnly, setWithCapturedOnly] = useState(false);
  const [withNetworkData, setWithNetworkData] = useState(false);
  
  // Input states (what user is typing/selecting)
  const [startDateInput, setStartDateInput] = useState<string>(getDefaultStartDate());
  const [endDateInput, setEndDateInput] = useState<string>(getDefaultEndDate());
  
  // Applied filter states (what's actually used in the query)
  const [startDate, setStartDate] = useState<string>(getDefaultStartDate());
  const [endDate, setEndDate] = useState<string>(getDefaultEndDate());
  
  const [isExporting, setIsExporting] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [journeyPage, setJourneyPage] = useState(1);
  const journeyPageSize = 200;

  const { data: journeys, isLoading } = useQuery(
    ['journeys', targetPath, withCapturedOnly, withNetworkData, startDate, endDate, currentPage, pageSize],
    () => analyticsAPI.listJourneys(targetPath || undefined, withCapturedOnly, withNetworkData, startDate, endDate, pageSize, (currentPage - 1) * pageSize),
    { refetchInterval: 60000 }
  );

  const { data: journeyDetail, isLoading: journeyDetailLoading, error: journeyDetailError } = useQuery(
    ['journey-detail', selectedClientId, journeyPage],
    () => selectedClientId ? analyticsAPI.getJourneyTimeline(selectedClientId, journeyPageSize, (journeyPage - 1) * journeyPageSize) : Promise.resolve(null),
    { enabled: !!selectedClientId }
  );

  useEffect(() => {
    setJourneyPage(1);
  }, [selectedClientId]);

  const applyFilters = () => {
    setTargetPath(targetPathInput.trim());
    setStartDate(startDateInput);
    setEndDate(endDateInput);
    setCurrentPage(1);
  };

  const handleExport = async () => {
    try {
      setIsExporting(true);
      const response = await analyticsAPI.exportJourneysCSV(
        targetPath || undefined,
        withCapturedOnly,
        withNetworkData,
        startDate,
        endDate
      );
      const contentDisposition = response.headers?.['content-disposition'] || '';
      const filenameMatch = contentDisposition.match(/filename=([^;]+)/i);
      const filename = filenameMatch ? filenameMatch[1].replace(/"/g, '') : `crawldoctor_journeys_${startDate}_to_${endDate}_${targetPath || 'all'}.csv`;
      const blob = response.data instanceof Blob ? response.data : new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Journeys export failed', err);
      alert('Export failed. Please try again or reduce the date range.');
    } finally {
      setIsExporting(false);
    }
  };

  const summaryLabel = useMemo(() => {
    let label = 'All journeys';
    if (targetPath) label = `Journeys containing "${targetPath}"`;
    if (startDate && endDate) label += ` from ${startDate} to ${endDate}`;
    return label;
  }, [targetPath, startDate, endDate]);

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Journeys</h1>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setCurrentPage(1); }}
            className="border border-gray-300 rounded-md px-3 py-2"
          >
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
            <option value={100}>100 / page</option>
          </select>
        </div>
        
        <div className="bg-white p-4 rounded-lg shadow space-y-3">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">From:</label>
              <input
                type="date"
                value={startDateInput}
                onChange={(e) => setStartDateInput(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">To:</label>
              <input
                type="date"
                value={endDateInput}
                onChange={(e) => setEndDateInput(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>
            <div className="flex-1"></div>
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="px-4 py-2 text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isExporting ? 'Exporting...' : 'Export CSV'}
            </button>
          </div>
          
          <div className="flex items-center space-x-4">
            <input
              type="text"
              value={targetPathInput}
              onChange={(e) => setTargetPathInput(e.target.value)}
              onKeyPress={(e) => { if (e.key === 'Enter') applyFilters(); }}
              placeholder="Filter by path (e.g. /demo or /demo, /articles - supports multiple paths)"
              className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm"
            />
            <button
              onClick={applyFilters}
              className="px-4 py-2 text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Apply Filter
            </button>
            {targetPath && (
              <button
                onClick={() => { setTargetPath(''); setTargetPathInput(''); setCurrentPage(1); }}
                className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-gray-200 hover:bg-gray-300"
              >
                Clear
              </button>
            )}
          </div>
          
          <div className="flex items-center space-x-6">
            <label className="flex items-center space-x-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={withCapturedOnly}
                onChange={(e) => { setWithCapturedOnly(e.target.checked); setCurrentPage(1); }}
              />
              <span>Only with captured data</span>
            </label>
            <label className="flex items-center space-x-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={withNetworkData}
                onChange={(e) => { setWithNetworkData(e.target.checked); setCurrentPage(1); }}
              />
              <span>Only with network data</span>
            </label>
            {(withCapturedOnly || withNetworkData || targetPath) && (
              <span className="text-sm text-gray-500 italic">
                {summaryLabel}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm text-gray-600">{summaryLabel}</div>
          {isLoading && <div className="text-sm text-gray-500">Loading...</div>}
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Captured Data</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Path Journey</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Referrer</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">First Seen</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Seen</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timeline</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {journeys?.journeys?.map((j: any) => (
                <tr key={j.client_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {j.client_id?.slice(0, 8)}...
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xl">
                    {(j.captured_data || j.email || j.name) ? (
                      <div className="space-y-1">
                        {(j.email || j.name) && (
                          <div>
                            {j.email ? `email: ${j.email}` : ''}
                            {j.email && j.name ? ' | ' : ''}
                            {j.name ? `name: ${j.name}` : ''}
                          </div>
                        )}
                        {j.captured_data && (
                          <div 
                            className="text-xs text-gray-700 break-words truncate max-w-xl" 
                            title={j.captured_data}
                            style={{ maxWidth: '400px' }}
                          >
                            {j.captured_data.length > 100 ? `${j.captured_data.slice(0, 100)}...` : j.captured_data}
                          </div>
                        )}
                      </div>
                    ) : '—'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-2xl">
                    <div
                      className="break-words"
                      title={j.path_sequence || ''}
                      style={{
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                      }}
                    >
                      {j.path_sequence || '—'}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs">
                    <div className="break-words">
                      {j.first_referrer || '—'}
                      {j.first_referrer_domain ? ` (${j.first_referrer_domain})` : ''}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {j.first_seen ? new Date(j.first_seen).toLocaleString() : '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {j.last_seen ? new Date(j.last_seen).toLocaleString() : '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatDuration(j.duration_seconds)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-700">
                    <button className="underline" onClick={() => setSelectedClientId(j.client_id)}>
                      View
                    </button>
                  </td>
                </tr>
              ))}
              {journeys?.journeys?.length === 0 && (
                <tr>
                  <td className="px-6 py-4 text-sm text-gray-500" colSpan={8}>
                    No journeys found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {journeys && journeys.total_pages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={!journeys.has_prev}
              className="px-4 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-600">Page {journeys.current_page} of {journeys.total_pages}</span>
            <button
              onClick={() => setCurrentPage(Math.min(journeys.total_pages, currentPage + 1))}
              disabled={!journeys.has_next}
              className="px-4 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {selectedClientId && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-10 mx-auto p-5 border w-11/12 md:w-3/4 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">User Journey: {selectedClientId.slice(0,8)}...</h3>
              <div className="flex items-center space-x-3">
                <button
                  onClick={() => setJourneyPage(Math.max(1, journeyPage - 1))}
                  disabled={!journeyDetail?.has_prev}
                  className="px-3 py-1 text-sm rounded-md bg-white border border-gray-300 text-gray-700 disabled:opacity-50"
                >
                  Prev
                </button>
                <button
                  onClick={() => setJourneyPage(journeyPage + 1)}
                  disabled={!journeyDetail?.has_next}
                  className="px-3 py-1 text-sm rounded-md bg-white border border-gray-300 text-gray-700 disabled:opacity-50"
                >
                  Next
                </button>
                <button onClick={() => setSelectedClientId(null)} className="text-gray-600 hover:text-gray-800">Close</button>
              </div>
            </div>
            {journeyDetailLoading ? (
              <div className="p-4">Loading...</div>
            ) : journeyDetailError ? (
              <div className="p-4 text-sm text-red-600">Failed to load timeline.</div>
            ) : journeyDetail ? (
              <div className="space-y-4 max-h-[70vh] overflow-y-auto">
                {(journeyDetail.timeline || []).length === 0 ? (
                  <div className="p-4 text-sm text-gray-500">No timeline items for this user yet.</div>
                ) : (
                  journeyDetail.timeline.map((item: any) => (
                    <div key={`${item.type}-${item.id}`} className="border rounded p-3">
                      <div className="text-xs text-gray-500">{item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}</div>
                      <div className="flex items-center space-x-2">
                        <div className="text-sm font-semibold capitalize">{item.type === 'visit' ? 'Page View' : item.event_type}</div>
                        {(item.source || item.medium || item.campaign) && (
                          <span className="inline-flex px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
                            {(item.source || '—')}/{(item.medium || '—')}/{(item.campaign || '—')}
                          </span>
                        )}
                        {item.tracking_id && (
                          <span className="inline-flex px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800">
                            {item.tracking_id}
                          </span>
                        )}
                      </div>
                      {item.page_url && (
                        <div className="text-sm text-blue-700 break-words">
                          <a href={item.page_url} target="_blank" rel="noopener noreferrer" className="underline">{item.page_url}</a>
                        </div>
                      )}
                      {item.type !== 'visit' && item.data && (
                        <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto">{JSON.stringify(item.data, null, 2)}</pre>
                      )}
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="p-4">No data</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Journeys;
