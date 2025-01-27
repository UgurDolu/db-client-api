import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Grid,
  Divider,
  Snackbar,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { logger } from '../services/logger';
import { SelectChangeEvent } from '@mui/material';

interface UserSettings {
  export_type: string;
  export_location: string;
  notification_enabled: boolean;
  default_db_username: string;
  default_db_tns: string;
}

const initialSettings: UserSettings = {
  export_type: 'csv',
  export_location: 'exports',
  notification_enabled: true,
  default_db_username: '',
  default_db_tns: '',
};

export default function UserSettingsPage() {
  const [settings, setSettings] = useState<UserSettings>(initialSettings);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const { logout } = useAuth();

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get<UserSettings>('http://localhost:8000/api/users/me/settings', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });
      setSettings(response.data);
      logger.info('User settings fetched successfully');
    } catch (error) {
      logger.error('Failed to fetch user settings', error);
      setError('Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setError('');
    try {
      await axios.put(
        'http://localhost:8000/api/users/me/settings',
        settings,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json',
          },
        }
      );
      logger.info('User settings updated successfully');
      setSuccessMessage('Settings saved successfully');
    } catch (error) {
      logger.error('Failed to update user settings', error);
      setError('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTextChange = (field: keyof UserSettings) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setSettings(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  const handleSelectChange = (field: keyof UserSettings) => (
    event: SelectChangeEvent<string>
  ) => {
    const value = event.target.value;
    setSettings(prev => ({
      ...prev,
      [field]: field === 'notification_enabled' ? value === 'true' : value
    }));
  };

  if (isLoading) {
    return (
      <Container maxWidth="md" sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          User Settings
        </Typography>
        <Typography color="text.secondary">
          Configure your preferences for query exports and notifications
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Export Settings */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Export Settings
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <FormControl fullWidth>
                  <InputLabel>Export Type</InputLabel>
                  <Select
                    value={settings.export_type}
                    onChange={handleSelectChange('export_type')}
                    label="Export Type"
                  >
                    <MenuItem value="csv">CSV</MenuItem>
                    <MenuItem value="excel">Excel</MenuItem>
                    <MenuItem value="json">JSON</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  fullWidth
                  label="Export Location"
                  value={settings.export_location}
                  onChange={handleTextChange('export_location')}
                  helperText="Default location for exported files"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Database Defaults */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Database Defaults
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                <TextField
                  fullWidth
                  label="Default Database Username"
                  value={settings.default_db_username}
                  onChange={handleTextChange('default_db_username')}
                  helperText="Will be pre-filled when creating new queries"
                />

                <TextField
                  fullWidth
                  label="Default Database TNS"
                  value={settings.default_db_tns}
                  onChange={handleTextChange('default_db_tns')}
                  helperText="Default TNS connection string"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Notification Settings */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Notification Settings
              </Typography>
              <FormControl fullWidth>
                <InputLabel>Notifications</InputLabel>
                <Select
                  value={settings.notification_enabled ? 'true' : 'false'}
                  onChange={handleSelectChange('notification_enabled')}
                  label="Notifications"
                >
                  <MenuItem value="true">Enabled</MenuItem>
                  <MenuItem value="false">Disabled</MenuItem>
                </Select>
              </FormControl>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Box sx={{ mt: 4, display: 'flex', justifyContent: 'flex-end', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          onClick={handleSave}
          disabled={isSaving}
          startIcon={isSaving ? <CircularProgress size={20} /> : <SaveIcon />}
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </Button>
      </Box>

      <Snackbar
        open={!!successMessage}
        autoHideDuration={6000}
        onClose={() => setSuccessMessage('')}
        message={successMessage}
      />
    </Container>
  );
} 