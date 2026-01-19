import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient } from '../utils/api';

interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_superuser: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('auth_token'));
  const [isLoading, setIsLoading] = useState(true);

  // Check if user is authenticated
  const isAuthenticated = Boolean(user && token);

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('auth_token');
      
      if (savedToken) {
        try {
          // Validate token and get user info
          apiClient.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
          const response = await apiClient.get('/api/v1/auth/me');
          setUser(response.data);
          setToken(savedToken);
        } catch (error) {
          // Token is invalid, remove it
          console.error('Token validation failed:', error);
          localStorage.removeItem('auth_token');
          setToken(null);
          setUser(null);
          delete apiClient.defaults.headers.common['Authorization'];
        }
      }
      
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await apiClient.post('/api/v1/auth/login', {
        username,
        password,
      });

      const { access_token, user: userData } = response.data;
      
      // Save token and user data
      localStorage.setItem('auth_token', access_token);
      setToken(access_token);
      setUser(userData);
      
      // Set default authorization header
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Login failed';
      throw new Error(message);
    }
  };

  const logout = () => {
    // Clear local storage
    localStorage.removeItem('auth_token');
    
    // Clear state
    setToken(null);
    setUser(null);
    
    // Remove authorization header
    delete apiClient.defaults.headers.common['Authorization'];
    
    // Optional: Call logout endpoint
    apiClient.post('/api/v1/auth/logout').catch(console.error);
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    logout,
    isLoading,
    isAuthenticated,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
