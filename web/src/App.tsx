import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, Box } from '@mui/material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { theme } from './theme';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import QueriesPage from './pages/QueriesPage';
import UserSettingsPage from './pages/UserSettingsPage';
import NavigationBar from './components/NavigationBar';
import { AuthProvider, useAuth } from './contexts/AuthContext';

const queryClient = new QueryClient();

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? (
    <>
      <NavigationBar />
      {children}
    </>
  ) : (
    <Navigate to="/login" />
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <Router>
            <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignUpPage />} />
                <Route
                  path="/"
                  element={
                    <PrivateRoute>
                      <QueriesPage />
                    </PrivateRoute>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <PrivateRoute>
                      <UserSettingsPage />
                    </PrivateRoute>
                  }
                />
              </Routes>
            </Box>
          </Router>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;
