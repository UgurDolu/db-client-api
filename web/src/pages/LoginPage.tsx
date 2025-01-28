import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { logger } from '../services/logger';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showServerCheck, setShowServerCheck] = useState(false);

  // Check if already authenticated
  useEffect(() => {
    logger.debug('LoginPage: Checking authentication state', { isAuthenticated });
    if (isAuthenticated) {
      logger.info('User already authenticated, redirecting to home');
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    // Clear error when inputs change
    if (error) {
      setError('');
    }
  }, [email, password]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    logger.debug('Login form submitted', { email });
    setError('');
    setIsLoading(true);
    setShowServerCheck(false);

    try {
      await login(email, password);
      logger.info('Login successful, redirecting to home');
      navigate('/', { replace: true });
    } catch (err: any) {
      const errorMessage = err.message;
      logger.error('Login failed', { error: errorMessage });
      setError(errorMessage);
      
      // Show server check message for connection errors
      if (errorMessage.includes('Unable to connect to the server')) {
        setShowServerCheck(true);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = () => {
    logger.debug('Navigating to sign up page');
    navigate('/signup');
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
        pt: '64px'
      }}
    >
      <Container maxWidth="xs">
        <Paper
          elevation={3}
          sx={{
            p: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
            borderRadius: 2
          }}
        >
          <Typography 
            component="h1" 
            variant="h5" 
            gutterBottom
            sx={{ fontWeight: 500 }}
          >
            Welcome Back
          </Typography>
          <Typography 
            variant="body2" 
            color="text.secondary" 
            sx={{ mb: 3 }}
          >
            Sign in to continue to DB Client
          </Typography>
          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{ mt: 1, width: '100%' }}
          >
            {error && (
              <Alert 
                severity="error" 
                sx={{ mb: 2 }}
                action={
                  showServerCheck && (
                    <Button 
                      color="inherit" 
                      size="small"
                      onClick={() => {
                        window.open('http://localhost:8000/docs', '_blank');
                      }}
                    >
                      Check Server
                    </Button>
                  )
                }
              >
                {error}
              </Alert>
            )}
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2, height: 36 }}
              disabled={isLoading}
            >
              {isLoading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                'Login'
              )}
            </Button>
            <Divider sx={{ my: 2 }}>or</Divider>
            <Button
              fullWidth
              variant="outlined"
              onClick={handleSignUp}
              sx={{ height: 36 }}
            >
              Create New Account
            </Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
} 