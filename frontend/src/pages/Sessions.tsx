import React, { useEffect, useState } from 'react';
import { useQuery } from 'react-query';
import { analyticsAPI } from '../utils/api';

const Sessions: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [jumpTo, setJumpTo] = useState<string>('');
  const [journeyPage, setJourneyPage] = useState(1);
  const journeyPageSize = 200;

  const { data: sessions } = useQuery(
    ['sessions', currentPage, pageSize],
    () => analyticsAPI.listSessions(pageSize, (currentPage - 1) * pageSize),
    { refetchInterval: 60000 }
  );

  const { data: sessionDetail, isLoading: sessionDetailLoading } = useQuery(
    ['session-detail', selectedSession],
    () => selectedSession ? analyticsAPI.getSessionDetail(selectedSession) : Promise.resolve(null),
    { enabled: !!selectedSession }
  );

  const { data: journeyDetail, isLoading: journeyDetailLoading } = useQuery(
    ['journey-detail', selectedClientId, journeyPage],
    () => selectedClientId ? analyticsAPI.getJourneyTimeline(selectedClientId, journeyPageSize, (journeyPage - 1) * journeyPageSize) : Promise.resolve(null),
    { enabled: !!selectedClientId }
  );

  useEffect(() => {
    setJourneyPage(1);
  }, [selectedClientId]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Sessions</h1>
        <div className="flex items-center space-x-4">
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
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Session</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">First Visit</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Visit</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Visits</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Browser Info</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Journey</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {sessions?.sessions?.map((s: any) => (
                <tr key={s.session_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-700">
                    <button className="underline" onClick={() => setSelectedSession(s.session_id)}>
                      {s.session_id.slice(0,8)}...
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {s.client_id ? s.client_id.slice(0, 8) + '...' : '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{s.first_visit ? new Date(s.first_visit).toLocaleString() : '—'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{s.last_visit ? new Date(s.last_visit).toLocaleString() : '—'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{s.visit_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      s.classification === 'AI Crawler' 
                        ? 'bg-red-100 text-red-800' 
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {s.classification || 'Unknown'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{s.city && s.country ? `${s.city}, ${s.country}` : '—'}</td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    <div className="text-xs space-y-1">
                      {s.client_side_language && <div>🌐 {s.client_side_language}</div>}
                      {s.client_side_screen_resolution && <div>📱 {s.client_side_screen_resolution}</div>}
                      {s.client_side_timezone && <div>🕐 {s.client_side_timezone}</div>}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-700">
                    {s.client_id ? (
                      <button className="underline" onClick={() => setSelectedClientId(s.client_id)}>
                        View
                      </button>
                    ) : (
                      '—'
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {sessions && sessions.total_pages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={!sessions.has_prev}
              className="px-4 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Page {sessions.current_page} of {sessions.total_pages}</span>
              <input
                type="number"
                min={1}
                max={sessions.total_pages}
                value={jumpTo}
                onChange={(e) => setJumpTo(e.target.value)}
                placeholder="#"
                className="w-20 border border-gray-300 rounded-md px-2 py-1 text-sm"
              />
              <button
                onClick={() => {
                  const num = parseInt(jumpTo || '');
                  if (!isNaN(num)) {
                    const page = Math.max(1, Math.min(sessions.total_pages, num));
                    setCurrentPage(page);
                  }
                }}
                className="px-3 py-2 text-sm font-medium rounded-md text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
              >
                Go
              </button>
            </div>
            <button
              onClick={() => setCurrentPage(Math.min(sessions.total_pages, currentPage + 1))}
              disabled={!sessions.has_next}
              className="px-4 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Session Timeline Modal */}
      {selectedSession && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-10 mx-auto p-5 border w-11/12 md:w-3/4 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Session Timeline: {selectedSession.slice(0,8)}...</h3>
              <div className="flex items-center space-x-3">
                {sessionDetail?.session?.client_id && (
                  <button
                    onClick={() => setSelectedClientId(sessionDetail.session.client_id)}
                    className="px-3 py-1 text-sm rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100"
                  >
                    View Journey
                  </button>
                )}
                <button onClick={() => setSelectedSession(null)} className="text-gray-600 hover:text-gray-800">Close</button>
              </div>
            </div>
            {sessionDetailLoading ? (
              <div className="p-4">Loading...</div>
            ) : sessionDetail ? (
              <div className="space-y-4 max-h-[70vh] overflow-y-auto">
                {sessionDetail.timeline.map((item: any) => (
                  <div key={`${item.type}-${item.id}`} className="border rounded p-3">
                    <div className="text-xs text-gray-500">{item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}</div>
                    <div className="flex items-center space-x-2">
                      <div className="text-sm font-semibold capitalize">{item.type === 'visit' ? 'Page View' : item.event_type}</div>
                      {item.crawler_type && (
                        <span className={`inline-flex px-2 py-0.5 text-xs rounded-full ${item.is_bot ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800'}`}>
                          {item.crawler_type}
                        </span>
                      )}
                      {(item.source || item.medium || item.campaign) && (
                        <span className="inline-flex px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
                          {(item.source || '—')}/{(item.medium || '—')}/{(item.campaign || '—')}
                        </span>
                      )}
                      {(item.tracking_id || item.tracking_method) && (
                        <span className="inline-flex px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800">
                          {(item.tracking_method || '—')}{item.tracking_id ? `:${item.tracking_id}` : ''}
                        </span>
                      )}
                      {(item.country || item.city) && (
                        <span className="inline-flex px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-800">
                          {(item.city || '')}{item.city && item.country ? ', ' : ''}{item.country || ''}
                        </span>
                      )}
                    </div>
                    {item.page_url && (
                      <div className="text-sm text-blue-700 break-words">
                        <a href={item.page_url} target="_blank" rel="noopener noreferrer" className="underline">{item.page_url}</a>
                      </div>
                    )}
                    {item.type !== 'visit' && (
                      <pre className="text-xs bg-gray-50 p-2 rounded overflow-auto">{JSON.stringify(item.data, null, 2)}</pre>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-4">No data</div>
            )}
          </div>
        </div>
      )}

      {/* User Journey Modal */}
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
            ) : journeyDetail ? (
              <div className="space-y-4 max-h-[70vh] overflow-y-auto">
                {journeyDetail.timeline.map((item: any) => (
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
                ))}
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

export default Sessions;


