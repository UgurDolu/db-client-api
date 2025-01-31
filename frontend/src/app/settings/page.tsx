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
} from '@mui/material';
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
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      {saveSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Settings saved successfully!
        </Alert>
      )}

      {saveError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {saveError}
        </Alert>
      )}

      <Card>
        <CardContent>
          <form onSubmit={formik.handleSubmit}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="export_location"
                  label="Default Export Location"
                  value={formik.values.export_location}
                  onChange={formik.handleChange}
                  error={
                    formik.touched.export_location &&
                    Boolean(formik.errors.export_location)
                  }
                  helperText={
                    formik.touched.export_location &&
                    formik.errors.export_location
                  }
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="export_type"
                  label="Default Export Type"
                  value={formik.values.export_type}
                  onChange={formik.handleChange}
                  error={
                    formik.touched.export_type &&
                    Boolean(formik.errors.export_type)
                  }
                  helperText={
                    formik.touched.export_type && formik.errors.export_type
                  }
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
                  error={
                    formik.touched.max_parallel_queries &&
                    Boolean(formik.errors.max_parallel_queries)
                  }
                  helperText={
                    formik.touched.max_parallel_queries &&
                    formik.errors.max_parallel_queries
                  }
                />
              </Grid>

              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                  SSH Settings
                </Typography>
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="ssh_hostname"
                  label="SSH Hostname"
                  value={formik.values.ssh_hostname}
                  onChange={formik.handleChange}
                  error={
                    formik.touched.ssh_hostname &&
                    Boolean(formik.errors.ssh_hostname)
                  }
                  helperText={
                    formik.touched.ssh_hostname && formik.errors.ssh_hostname
                  }
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
                  error={
                    formik.touched.ssh_port && Boolean(formik.errors.ssh_port)
                  }
                  helperText={formik.touched.ssh_port && formik.errors.ssh_port}
                />
              </Grid>

              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  name="ssh_username"
                  label="SSH Username"
                  value={formik.values.ssh_username}
                  onChange={formik.handleChange}
                  error={
                    formik.touched.ssh_username &&
                    Boolean(formik.errors.ssh_username)
                  }
                  helperText={
                    formik.touched.ssh_username && formik.errors.ssh_username
                  }
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
                  error={
                    formik.touched.ssh_password &&
                    Boolean(formik.errors.ssh_password)
                  }
                  helperText={
                    formik.touched.ssh_password && formik.errors.ssh_password
                  }
                />
              </Grid>

              <Grid item xs={12}>
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  sx={{ mt: 2 }}
                >
                  Save Settings
                </Button>
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
} 