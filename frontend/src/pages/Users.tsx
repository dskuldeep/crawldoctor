import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { analyticsAPI } from '../utils/api';

const Users: React.FC = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [jumpTo, setJumpTo] = useState<string>('');

  const { data: users } = useQuery(
    ['unified-users', currentPage, pageSize],
    () => analyticsAPI.listUnifiedUsers(pageSize, (currentPage - 1) * pageSize),
    { refetchInterval: 60000 }
  );

  const { data: userActivity, isLoading: userActivityLoading } = useQuery(
    ['user-activity', selectedUser],
    () => selectedUser ? analyticsAPI.getUnifiedUserActivity(selectedUser) : Promise.resolve(null),
    { enabled: !!selectedUser }
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Unified Users</h1>
          <p className="text-sm text-gray-600 mt-1">
            Track individual users across multiple sessions and domains using persistent client IDs
          </p>
        </div>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sessions</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Visits</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Events</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">First Seen</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Seen</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {users?.users?.map((user: any) => (
                <tr key={user.client_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-700">
                    <button className="underline font-mono" onClick={() => setSelectedUser(user.client_id)}>
                      {user.client_id.slice(0, 12)}...
                    </button>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.session_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.visit_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.event_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {user.first_seen ? new Date(user.first_seen).toLocaleString() : '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {user.last_seen ? new Date(user.last_seen).toLocaleString() : '—'}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {user.last_city && user.last_country ? `${user.last_city}, ${user.last_country}` : 'Unknown'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {users && users.total_pages > 1 && (
          <div className="mt-4 flex items-center justify-between">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={!users.has_prev}
              className="px-4 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">Page {users.current_page} of {users.total_pages}</span>
              <input
                type="number"
                min={1}
                max={users.total_pages}
                value={jumpTo}
                onChange={(e) => setJumpTo(e.target.value)}
                placeholder="#"
                className="w-20 border border-gray-300 rounded-md px-2 py-1 text-sm"
              />
              <button
                onClick={() => {
                  const num = parseInt(jumpTo || '');
                  if (!isNaN(num)) {
                    const page = Math.max(1, Math.min(users.total_pages, num));
                    setCurrentPage(page);
                  }
                }}
                className="px-3 py-2 text-sm font-medium rounded-md text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
              >
                Go
              </button>
            </div>
            <button
              onClick={() => setCurrentPage(Math.min(users.total_pages, currentPage + 1))}
              disabled={!users.has_next}
              className="px-4 py-2 text-sm font-medium text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* User Activity Modal */}
      {selectedUser && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-10 mx-auto p-5 border w-11/12 md:w-3/4 shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h3 className="text-lg font-medium text-gray-900">User Activity</h3>
                <p className="text-sm text-gray-500 font-mono">{selectedUser}</p>
              </div>
              <button
                onClick={() => setSelectedUser(null)}
                className="text-gray-600 hover:text-gray-800 text-2xl leading-none"
              >
                ×
              </button>
            </div>

            {userActivityLoading ? (
              <div className="p-4">Loading...</div>
            ) : userActivity ? (
              <div className="space-y-6">
                {/* Summary Stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Sessions</div>
                    <div className="text-2xl font-bold text-blue-700">{userActivity.summary?.unique_sessions || 0}</div>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Visits</div>
                    <div className="text-2xl font-bold text-green-700">{userActivity.summary?.total_visits || 0}</div>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Events</div>
                    <div className="text-2xl font-bold text-purple-700">{userActivity.summary?.total_events || 0}</div>
                  </div>
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <div className="text-sm text-gray-600">Domains</div>
                    <div className="text-2xl font-bold text-orange-700">{userActivity.summary?.unique_domains || 0}</div>
                  </div>
                </div>

                {/* Sessions List */}
                <div>
                  <h4 className="text-md font-semibold text-gray-800 mb-2">Sessions</h4>
                  <div className="bg-gray-50 rounded-lg p-4 max-h-40 overflow-y-auto">
                    {userActivity.sessions?.map((session: any) => (
                      <div key={session.session_id} className="border-b border-gray-200 py-2 last:border-b-0">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="text-xs font-mono text-gray-500">{session.session_id.slice(0, 16)}...</div>
                            <div className="text-sm text-gray-700">
                              {session.city && session.country ? `${session.city}, ${session.country}` : 'Location unknown'}
                            </div>
                          </div>
                          <div className="text-xs text-gray-500 text-right">
                            <div>First: {session.first_visit ? new Date(session.first_visit).toLocaleString() : '—'}</div>
                            <div>Last: {session.last_visit ? new Date(session.last_visit).toLocaleString() : '—'}</div>
                            <div>{session.visit_count} visits</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Timeline */}
                <div>
                  <h4 className="text-md font-semibold text-gray-800 mb-2">Complete Timeline</h4>
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {userActivity.timeline?.map((item: any, index: number) => (
                      <div key={`${item.type}-${item.id}-${index}`} className="border rounded-lg p-3 hover:bg-gray-50">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center space-x-2">
                            <span className={`inline-flex px-2 py-0.5 text-xs rounded-full font-semibold ${item.type === 'visit'
                                ? 'bg-green-100 text-green-800'
                                : 'bg-purple-100 text-purple-800'
                              }`}>
                              {item.type === 'visit' ? 'Page View' : item.event_type || 'Event'}
                            </span>
                            {item.is_bot !== undefined && (
                              <span className={`inline-flex px-2 py-0.5 text-xs rounded-full ${item.is_bot ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
                                }`}>
                                {item.is_bot ? 'Bot' : 'Human'}
                              </span>
                            )}
                          </div>
                          <div className="text-xs text-gray-500">
                            {item.timestamp ? new Date(item.timestamp).toLocaleString() : '—'}
                          </div>
                        </div>

                        {item.page_url && (
                          <div className="text-sm text-blue-600 break-all mb-1">
                            <a href={item.page_url} target="_blank" rel="noopener noreferrer" className="hover:underline">
                              {item.page_url}
                            </a>
                          </div>
                        )}

                        <div className="flex flex-wrap gap-2 text-xs">
                          {item.country && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                              📍 {item.city ? `${item.city}, ` : ''}{item.country}
                            </span>
                          )}
                          {item.source && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                              Source: {item.source}
                            </span>
                          )}
                          {item.medium && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                              Medium: {item.medium}
                            </span>
                          )}
                          {item.campaign && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-700">
                              Campaign: {item.campaign}
                            </span>
                          )}
                        </div>

                        {item.type === 'event' && item.event_type === 'form_submit' && item.data ? (
                          <div className="mt-2 text-xs bg-green-50 border border-green-200 rounded p-2">
                            <div className="font-semibold text-green-800 mb-1 flex justify-between">
                              <span>📝 Form Submission</span>
                              <span>{item.data.filled_fields || 0} fields filled</span>
                            </div>
                            {item.data.form_values && Object.keys(item.data.form_values).length > 0 && (
                              <div className="mt-1 space-y-1">
                                {Object.entries(item.data.form_values).map(([key, val]) => (
                                  <div key={key} className="flex gap-2 border-b last:border-0 border-green-100 py-1">
                                    <span className="font-medium text-green-700 w-1/3 truncate" title={key}>{key}:</span>
                                    <span className="text-green-900 flex-1 break-all">{String(val)}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ) : item.type === 'event' && item.data && (
                          <details className="mt-2">
                            <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                              Event Data
                            </summary>
                            <pre className="text-xs bg-gray-50 p-2 rounded mt-1 overflow-auto max-h-40">
                              {JSON.stringify(item.data, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
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

export default Users;

