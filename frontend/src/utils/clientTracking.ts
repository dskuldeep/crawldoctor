/**
 * Client-side tracking utility to capture browser and location data
 */

interface ClientSideData {
  location_city?: string;
  location_country?: string;
  timezone?: string;
  language?: string;
  screen_resolution?: string;
  viewport_size?: string;
  device_memory?: string;
  connection_type?: string;
}

/**
 * Get client-side data from browser APIs
 */
export async function getClientSideData(): Promise<ClientSideData> {
  const data: ClientSideData = {};

  try {
    // Capture timezone
    data.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch (e) {
    console.warn('Could not capture timezone', e);
  }

  try {
    // Capture language
    data.language = navigator.language || (navigator as any).userLanguage;
  } catch (e) {
    console.warn('Could not capture language', e);
  }

  try {
    // Capture screen resolution
    data.screen_resolution = `${window.screen.width}x${window.screen.height}`;
  } catch (e) {
    console.warn('Could not capture screen resolution', e);
  }

  try {
    // Capture viewport size
    data.viewport_size = `${window.innerWidth}x${window.innerHeight}`;
  } catch (e) {
    console.warn('Could not capture viewport size', e);
  }

  try {
    // Capture device memory (if available)
    const nav = navigator as any;
    if (nav.deviceMemory) {
      data.device_memory = `${nav.deviceMemory}GB`;
    }
  } catch (e) {
    console.warn('Could not capture device memory', e);
  }

  try {
    // Capture connection type (if available)
    const nav = navigator as any;
    if (nav.connection) {
      data.connection_type = nav.connection.effectiveType || nav.connection.type;
    }
  } catch (e) {
    console.warn('Could not capture connection type', e);
  }

  // Try to get location from browser geolocation API
  try {
    const location = await getGeolocation();
    if (location) {
      // Use reverse geocoding service to get city/country from coordinates
      const geoData = await reverseGeocode(location.latitude, location.longitude);
      if (geoData) {
        data.location_city = geoData.city;
        data.location_country = geoData.country;
      }
    }
  } catch (e) {
    console.warn('Could not capture location', e);
  }

  return data;
}

/**
 * Get geolocation from browser (requires user permission)
 */
function getGeolocation(): Promise<{ latitude: number; longitude: number } | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(null);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
      },
      (error) => {
        console.warn('Geolocation error:', error);
        resolve(null);
      },
      {
        timeout: 5000,
        maximumAge: 600000, // Cache for 10 minutes
      }
    );
  });
}

/**
 * Reverse geocode coordinates to get city/country
 * Using OpenStreetMap's Nominatim service (free, no API key required)
 */
async function reverseGeocode(
  latitude: number,
  longitude: number
): Promise<{ city?: string; country?: string } | null> {
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=10&addressdetails=1`,
      {
        headers: {
          'User-Agent': 'CrawlDoctor-Analytics',
        },
      }
    );

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    const address = data.address || {};

    return {
      city: address.city || address.town || address.village || address.hamlet,
      country: address.country,
    };
  } catch (error) {
    console.warn('Reverse geocoding failed:', error);
    return null;
  }
}

/**
 * Get or create client ID (persistent identifier stored in localStorage)
 */
export function getOrCreateClientId(): string {
  const KEY = 'crawldoctor_client_id';
  try {
    let clientId = localStorage.getItem(KEY);
    if (!clientId) {
      clientId = generateUUID();
      localStorage.setItem(KEY, clientId);
    }
    return clientId;
  } catch (e) {
    // Fallback if localStorage is not available
    return generateUUID();
  }
}

/**
 * Generate a UUID v4
 */
function generateUUID(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Track an event with client-side data
 */
export async function trackEvent(eventType: string, eventData?: any): Promise<void> {
  try {
    const clientId = getOrCreateClientId();
    const clientSideData = await getClientSideData();

    const payload = {
      event_type: eventType,
      page_url: window.location.href,
      referrer: document.referrer,
      data: eventData,
      cid: clientId,
      client_side_data: clientSideData,
    };

    await fetch('/api/v1/track/event', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    console.error('Failed to track event:', error);
  }
}

/**
 * Initialize tracking on page load
 */
export function initTracking(): void {
  // Track page view on load
  trackEvent('page_view');

  // Track visibility changes
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      trackEvent('page_visible');
    } else {
      trackEvent('page_hidden');
    }
  });

  // Track page unload
  window.addEventListener('beforeunload', () => {
    trackEvent('page_unload');
  });
}

