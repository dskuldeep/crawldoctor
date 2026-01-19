import React, { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useNotification } from '../contexts/NotificationContext';
import LoadingSpinner from '../components/LoadingSpinner';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const { showNotification } = useNotification();
  const location = useLocation();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      const from = (location.state as any)?.from?.pathname || '/dashboard';
      window.location.href = from;
    }
  }, [isAuthenticated, authLoading, location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!username || !password) {
      showNotification({
        type: 'error',
        title: 'Validation Error',
        message: 'Please enter both username and password'
      });
      return;
    }

    setIsLoading(true);
    try {
      await login(username, password);
      showNotification({
        type: 'success',
        title: 'Login Successful',
        message: 'Welcome to CrawlDoctor!'
      });
    } catch (error: any) {
      showNotification({
        type: 'error',
        title: 'Login Failed',
        message: error.message || 'Invalid credentials'
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Show loading if checking auth state
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  // Redirect if already authenticated
  if (isAuthenticated) {
    const from = (location.state as any)?.from?.pathname || '/dashboard';
    return <Navigate to={from} replace />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-16 w-16 flex items-center justify-center rounded-full bg-primary-100">
            <span className="text-2xl">🕷️</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to CrawlDoctor
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            AI Crawler Tracking & Analytics Dashboard
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="username" className="sr-only">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm"
                placeholder="Username or email"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                disabled={isLoading}
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-primary-500 focus:border-primary-500 focus:z-10 sm:text-sm"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <LoadingSpinner size="small" label="" />
              ) : (
                'Sign in'
              )}
            </button>
          </div>

          {/* <div className="text-center">
            <div className="text-sm text-gray-600">
              Default admin credentials:
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Username: <code className="bg-gray-100 px-1 rounded">admin</code> | 
              Password: <code className="bg-gray-100 px-1 rounded">admin123</code>
            </div>
          </div> */}
        </form>

        <div className="mt-8 border-t border-gray-200 pt-6">
          <div className="text-center text-sm text-gray-500">
            <p>Features:</p>
            <ul className="mt-2 space-y-1">
              <li>🤖 AI Crawler Detection</li>
              <li>📊 Real-time Analytics</li>
              <li>🌍 Geographic Tracking</li>
              <li>🔒 Secure Dashboard</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
