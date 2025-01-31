'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid,
  TextField,
  Typography,
  Alert,
  CircularProgress,
  Divider,
  Paper,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Save as SaveIcon,
  Settings as SettingsIcon,
  Folder as FolderIcon,
  Code as CodeIcon,
  Speed as SpeedIcon,
  Computer as ComputerIcon,
  Numbers as PortIcon,
  Person as UserIcon,
  Key as PasswordIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as yup from 'yup';
import { apiClient, UserSettings } from '../../service/api';

const validationSchema = yup.object({
  export_location: yup.string(),
  export_type: yup.string(),
  max_parallel_queries: yup
    .number()
    .min(1, 'Must be at least 1')
    .max(100, 'Must be at most 100'),
  ssh_hostname: yup.string(),
  ssh_port: yup.number().min(1).max(65535),
  ssh_username: yup.string(),
  ssh_password: yup.string(),
});

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const formik = useFormik({
    initialValues: {
      export_location: '',
      export_type: '',
      max_parallel_queries: 10,
      ssh_hostname: '',
      ssh_port: 22,
      ssh_username: '',
      ssh_password: '',
    },
    validationSchema: validationSchema,
    onSubmit: async (values) => {
      try {
        await apiClient.users.updateSettings(values);
        setSaveSuccess(true);
        setSaveError(null);
        setTimeout(() => setSaveSuccess(false), 3000);
      } catch (error) {
        console.error('Error saving settings:', error);
        setSaveError('Failed to save settings. Please try again.');
      }
    },
  });

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await apiClient.users.getSettings();
        formik.setValues({
          ...formik.values,
          ...response.data,
        });
      } catch (error) {
        console.error('Error fetching settings:', error);
        setSaveError('Failed to load settings. Please refresh the page.');
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, []);

  if (loading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '60vh',
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <SettingsIcon color="primary" fontSize="large" />
          <Typography variant="h4">Settings</Typography>
        </Box>
        <Tooltip title="Save Settings">
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={() => formik.handleSubmit()}
            sx={{ borderRadius: 2 }}
          >
            Save Changes
          </Button>
        </Tooltip>
      </Box>

      {saveSuccess && (
        <Alert 
          severity="success" 
          sx={{ mb: 2 }}
          icon={<InfoIcon />}
        >
          Settings saved successfully!
        </Alert>
      )}

      {saveError && (
        <Alert 
          severity="error" 
          sx={{ mb: 2 }}
          icon={<InfoIcon />}
        >
          {saveError}
        </Alert>
      )}

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={3}>
            <CodeIcon color="primary" />
            <Typography variant="h6">Export Settings</Typography>
          </Box>
          <form onSubmit={formik.handleSubmit}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="export_location"
                  label="Default Export Location"
                  value={formik.values.export_location}
                  onChange={formik.handleChange}
                  error={formik.touched.export_location && Boolean(formik.errors.export_location)}
                  helperText={formik.touched.export_location && formik.errors.export_location}
                  InputProps={{
                    startAdornment: <FolderIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="export_type"
                  label="Default Export Type"
                  value={formik.values.export_type}
                  onChange={formik.handleChange}
                  error={formik.touched.export_type && Boolean(formik.errors.export_type)}
                  helperText={formik.touched.export_type && formik.errors.export_type}
                  InputProps={{
                    startAdornment: <CodeIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  name="max_parallel_queries"
                  label="Max Parallel Queries"
                  value={formik.values.max_parallel_queries}
                  onChange={formik.handleChange}
                  error={formik.touched.max_parallel_queries && Boolean(formik.errors.max_parallel_queries)}
                  helperText={formik.touched.max_parallel_queries && formik.errors.max_parallel_queries}
                  InputProps={{
                    startAdornment: <SpeedIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={3}>
            <ComputerIcon color="primary" />
            <Typography variant="h6">SSH Settings</Typography>
          </Box>
          <form onSubmit={formik.handleSubmit}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="ssh_hostname"
                  label="SSH Hostname"
                  value={formik.values.ssh_hostname}
                  onChange={formik.handleChange}
                  error={formik.touched.ssh_hostname && Boolean(formik.errors.ssh_hostname)}
                  helperText={formik.touched.ssh_hostname && formik.errors.ssh_hostname}
                  InputProps={{
                    startAdornment: <ComputerIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="number"
                  name="ssh_port"
                  label="SSH Port"
                  value={formik.values.ssh_port}
                  onChange={formik.handleChange}
                  error={formik.touched.ssh_port && Boolean(formik.errors.ssh_port)}
                  helperText={formik.touched.ssh_port && formik.errors.ssh_port}
                  InputProps={{
                    startAdornment: <PortIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="ssh_username"
                  label="SSH Username"
                  value={formik.values.ssh_username}
                  onChange={formik.handleChange}
                  error={formik.touched.ssh_username && Boolean(formik.errors.ssh_username)}
                  helperText={formik.touched.ssh_username && formik.errors.ssh_username}
                  InputProps={{
                    startAdornment: <UserIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  type="password"
                  name="ssh_password"
                  label="SSH Password"
                  value={formik.values.ssh_password}
                  onChange={formik.handleChange}
                  error={formik.touched.ssh_password && Boolean(formik.errors.ssh_password)}
                  helperText={formik.touched.ssh_password && formik.errors.ssh_password}
                  InputProps={{
                    startAdornment: <PasswordIcon color="action" sx={{ mr: 1 }} />,
                  }}
                />
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
} 