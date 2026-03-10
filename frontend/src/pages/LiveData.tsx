import React, { useEffect, useState, useRef } from 'react';
import { analyticsAPI } from '../utils/api';

interface LiveEvent {
  id: number;
  timestamp: string;
  event_type: string;
  page_url: string;
  path?: string;
  referrer?: string;
  client_id?: string;
  session_id?: string;
  event_data?: any;
  source?: string;
  medium?: string;
  campaign?: string;
}

const LiveData: React.FC = () => {
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState<string>('');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch initial events
  const fetchEvents = async () => {
    try {
      const data = await analyticsAPI.getLiveEvents(100);
      if (data.events && Array.isArray(data.events)) {
        setEvents(data.events);
      }
    } catch (error) {
      console.error('Failed to fetch live events:', error);
    }
  };

  // Setup polling as fallback (SSE might not work in all environments)
  useEffect(() => {
    const setupPolling = () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }

      fetchEvents();
      
      pollingIntervalRef.current = setInterval(() => {
        if (!isPaused) {
          fetchEvents();
        }
      }, 3000); // Poll every 3 seconds
    };
    // Try SSE first, fall back to polling
    try {
      const eventSource = new EventSource('/api/v1/analytics/live-stream');
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        console.log('Live stream connected');
      };

      eventSource.onmessage = (event) => {
        if (!isPaused) {
          try {
            const newEvent = JSON.parse(event.data);
            setEvents((prev) => [newEvent, ...prev.slice(0, 99)]);
          } catch (e) {
            console.error('Failed to parse event:', e);
          }
        }
      };

      eventSource.onerror = (error) => {
        console.log('SSE error, falling back to polling:', error);
        setIsConnected(false);
        eventSource.close();
        setupPolling();
      };
    } catch (error) {
      console.log('SSE not supported, using polling');
      setupPolling();
    }

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [isPaused]);

  // Filter events
  const filteredEvents = events.filter((event) => {
    if (eventTypeFilter !== 'all' && event.event_type !== eventTypeFilter) {
      return false;
    }
    if (filter && !JSON.stringify(event).toLowerCase().includes(filter.toLowerCase())) {
      return false;
    }
    return true;
  });

  // Get unique event types for filter dropdown
  const eventTypes = ['all', ...Array.from(new Set(events.map(e => e.event_type)))];

  const getEventColor = (eventType: string) => {
    const colors: Record<string, string> = {
      page_view: 'bg-blue-100 text-blue-800',
      click: 'bg-green-100 text-green-800',
      form_submit: 'bg-purple-100 text-purple-800',
      form_input: 'bg-yellow-100 text-yellow-800',
      scroll: 'bg-gray-100 text-gray-800',
      navigation: 'bg-indigo-100 text-indigo-800',
      heartbeat: 'bg-pink-100 text-pink-800',
      visibility: 'bg-orange-100 text-orange-800',
    };
    return colors[eventType] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Live Data</h1>
          <p className="text-sm text-gray-500">
            Real-time tracking events as they happen
            {isConnected && <span className="ml-2 text-green-600">● Connected</span>}
            {!isConnected && <span className="ml-2 text-orange-600">● Polling</span>}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsPaused(!isPaused)}
            className={`px-4 py-2 text-sm font-medium rounded-md ${
              isPaused
                ? 'bg-green-600 text-white hover:bg-green-700'
                : 'bg-red-600 text-white hover:bg-red-700'
            }`}
          >
            {isPaused ? 'Resume' : 'Pause'}
          </button>
          <button
            onClick={() => setEvents([])}
            className="px-4 py-2 text-sm font-medium rounded-md text-gray-700 bg-white border border-gray-300 hover:bg-gray-50"
          >
            Clear
          </button>
        </div>
      </div>

      <div className="bg-white p-4 rounded-lg shadow space-y-3">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Event Type:</label>
            <select
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm"
            >
              {eventTypes.map((type) => (
                <option key={type} value={type}>
                  {type === 'all' ? 'All Events' : type}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center space-x-2">
            <label className="text-sm font-medium text-gray-700">Search:</label>
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter events..."
              className="border border-gray-300 rounded-md px-3 py-2 text-sm w-64"
            />
          </div>
          <div className="text-sm text-gray-600">
            Showing {filteredEvents.length} of {events.length} events
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="max-h-[calc(100vh-300px)] overflow-y-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 sticky top-0 z-10">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Time
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Event Type
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Page
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Client ID
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Source
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Data
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-500">
                    {isPaused ? 'Paused - Click Resume to continue' : 'Waiting for events...'}
                  </td>
                </tr>
              ) : (
                filteredEvents.map((event) => (
                  <tr key={`${event.id}-${event.timestamp}`} className="hover:bg-gray-50">
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-gray-500">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getEventColor(
                          event.event_type
                        )}`}
                      >
                        {event.event_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-900 max-w-xs truncate">
                      {event.path || event.page_url || '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700 font-mono">
                      {event.client_id ? event.client_id.slice(0, 8) + '...' : '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">
                      {event.source || 'direct'} / {event.medium || 'none'}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {event.event_data && Object.keys(event.event_data).length > 0 ? (
                        <details className="cursor-pointer">
                          <summary className="text-blue-600 hover:text-blue-800">View</summary>
                          <pre className="mt-2 p-2 bg-gray-50 rounded text-xs max-w-md overflow-auto">
                            {JSON.stringify(event.event_data, null, 2)}
                          </pre>
                        </details>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default LiveData;
