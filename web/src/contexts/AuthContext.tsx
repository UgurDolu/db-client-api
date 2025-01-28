import { createContext, useContext, useState, useEffect } from 'react';
import axios, { AxiosError } from 'axios';
import { logger } from '../services/logger';
import api from '../services/api';
import { User } from '../types/api';

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const getErrorMessage = (error: any): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail?: string }>;
    if (!axiosError.response) {
      // Network error
      if (axiosError.code === 'ERR_NETWORK' || axiosError.message.includes('Network Error')) {
        return 'Unable to connect to the server. Please check if the server is running and try again.';
      }
      return 'Network error occurred. Please check your internet connection.';
    }
    // Server error with response
    return axiosError.response.data?.detail || 'Server error occurred';
  }
  return error?.message || 'An unexpected error occurred';
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      logger.debug('Token found in localStorage, restoring session');
      setIsAuthenticated(true);
      fetchUserData();
    } else {
      logger.debug('No token found in localStorage');
    }
  }, []);

  const fetchUserData = async () => {
    try {
      logger.debug('Fetching user data');
      const userData = await api.user.getProfile();
      logger.info('User data fetched successfully', { userId: userData.id });
      setUser(userData);
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      logger.error('Error fetching user data', { 
        error: errorMessage,
        details: {
          code: (error as AxiosError)?.code,
          status: (error as AxiosError)?.response?.status,
          url: '/users/profile'
        }
      });
      logout();
    }
  };

  const login = async (email: string, password: string) => {
    try {
      logger.debug('Attempting login', { 
        email,
        url: 'http://localhost:8000/api/auth/login'
      });

      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await axios.post(
        'http://localhost:8000/api/auth/login',
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          timeout: 5000, // 5 second timeout
        }
      );

      logger.debug('Login response received', { 
        status: response.status,
        hasToken: !!response.data.access_token 
      });

      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      logger.debug('Token stored in localStorage');
      
      setIsAuthenticated(true);
      logger.info('Authentication state updated', { isAuthenticated: true });
      
      await fetchUserData();
      logger.debug('Login process completed successfully');
    } catch (error) {
      const errorMessage = getErrorMessage(error);
      logger.error('Login failed', {
        error: errorMessage,
        details: {
          code: (error as AxiosError)?.code,
          status: (error as AxiosError)?.response?.status,
          url: 'http://localhost:8000/api/auth/login'
        }
      });
      throw new Error(errorMessage);
    }
  };

  const logout = () => {
    logger.info('User logged out');
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
  };

  logger.debug('AuthContext state', { isAuthenticated, hasUser: !!user });

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    logger.error('useAuth must be used within an AuthProvider');
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
} 