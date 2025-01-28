import { useState, useEffect } from 'react';
import {
  Container,
  Typography,
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
  Snackbar,
  IconButton,
} from '@mui/material';
import { Save as SaveIcon, VpnKey as VpnKeyIcon } from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { logger } from '../services/logger';
import { SelectChangeEvent } from '@mui/material';
import { userApi } from '../services/api';

interface UserSettings {
  export_type: string;
  export_location: string;
  max_parallel_queries: number;
  ssh_username: string;
  ssh_password: string;
  ssh_key: string;
  ssh_key_passphrase: string;
}

const initialSettings: UserSettings = {
  export_type: 'csv',
  export_location: 'exports',
  max_parallel_queries: 3,
  ssh_username: '',
  ssh_password: '',
  ssh_key: '',
  ssh_key_passphrase: '',
};

export default function UserSettingsPage() {
  const [settings, setSettings] = useState<UserSettings>(initialSettings);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTestingSSH, setIsTestingSSH] = useState(false);
  const [error, setError] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const { logout } = useAuth();

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const data = await userApi.getSettings();
      setSettings(data);
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
      await userApi.updateSettings(settings);
      logger.info('User settings updated successfully');
      setSuccessMessage('Settings saved successfully');
    } catch (error) {
      logger.error('Failed to update user settings', error);
      setError('Failed to save settings');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestSSH = async () => {
    setIsTestingSSH(true);
    setError('');
    try {
      const sshSettings = {
        ssh_username: settings.ssh_username,
        ssh_password: settings.ssh_password,
        ssh_key: settings.ssh_key,
        ssh_key_passphrase: settings.ssh_key_passphrase,
      };
      const response = await userApi.testSSHConnection(sshSettings);
      setSuccessMessage('SSH connection test successful');
      logger.info('SSH connection test successful', response);
    } catch (error) {
      logger.error('SSH connection test failed', error);
      setError('SSH connection test failed');
    } finally {
      setIsTestingSSH(false);
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
    setSettings(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  if (isLoading) {
    return (
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh',
        pt: '64px'
      }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ 
      minHeight: '100vh',
      pt: '84px',
      pb: 4,
      bgcolor: 'background.default'
    }}>
      <Container maxWidth="md">
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" component="h1" gutterBottom sx={{ fontWeight: 500 }}>
            Settings
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure your preferences for exports and SSH connections
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
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
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
                      <MenuItem value="feather">Feather</MenuItem>
                    </Select>
                  </FormControl>

                  <TextField
                    fullWidth
                    label="Export Location"
                    value={settings.export_location}
                    onChange={handleTextChange('export_location')}
                    helperText="Default location for exported files"
                  />

                  <TextField
                    fullWidth
                    type="number"
                    label="Max Parallel Queries"
                    value={settings.max_parallel_queries}
                    onChange={handleTextChange('max_parallel_queries')}
                    helperText="Maximum number of queries that can run in parallel"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          {/* SSH Settings */}
          <Grid item xs={12}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
                  SSH Settings
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <TextField
                    fullWidth
                    label="SSH Username"
                    value={settings.ssh_username}
                    onChange={handleTextChange('ssh_username')}
                  />

                  <TextField
                    fullWidth
                    type="password"
                    label="SSH Password"
                    value={settings.ssh_password}
                    onChange={handleTextChange('ssh_password')}
                  />

                  <TextField
                    fullWidth
                    multiline
                    rows={4}
                    label="SSH Key"
                    value={settings.ssh_key}
                    onChange={handleTextChange('ssh_key')}
                    helperText="Paste your private SSH key here"
                  />

                  <TextField
                    fullWidth
                    type="password"
                    label="SSH Key Passphrase"
                    value={settings.ssh_key_passphrase}
                    onChange={handleTextChange('ssh_key_passphrase')}
                  />

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Button
                      variant="outlined"
                      startIcon={<VpnKeyIcon />}
                      onClick={handleTestSSH}
                      disabled={isTestingSSH}
                    >
                      {isTestingSSH ? 'Testing Connection...' : 'Test SSH Connection'}
                    </Button>
                    <Button
                      variant="contained"
                      startIcon={<SaveIcon />}
                      onClick={handleSave}
                      disabled={isSaving}
                    >
                      {isSaving ? 'Saving...' : 'Save Changes'}
                    </Button>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Snackbar
          open={Boolean(successMessage)}
          autoHideDuration={6000}
          onClose={() => setSuccessMessage('')}
          message={successMessage}
        />
      </Container>
    </Box>
  );
} 