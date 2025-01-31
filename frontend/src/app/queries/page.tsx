'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  TextField,
  Typography,
  IconButton,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as yup from 'yup';
import { apiClient, Query } from '../../lib/api';

const validationSchema = yup.object({
  query_text: yup.string().required('Query is required'),
  db_username: yup.string().required('Database username is required'),
  db_password: yup.string().required('Database password is required'),
  db_tns: yup.string().required('Database TNS is required'),
  export_location: yup.string(),
  export_type: yup.string(),
  export_filename: yup.string(),
  ssh_hostname: yup.string(),
});

export default function QueriesPage() {
  const [queries, setQueries] = useState<Query[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchQueries = async () => {
    try {
      const response = await apiClient.queries.list();
      setQueries(response.data);
    } catch (error) {
      console.error('Error fetching queries:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueries();
  }, []);

  const formik = useFormik({
    initialValues: {
      query_text: '',
      db_username: '',
      db_password: '',
      db_tns: '',
      export_location: '',
      export_type: '',
      export_filename: '',
      ssh_hostname: '',
    },
    validationSchema: validationSchema,
    onSubmit: async (values) => {
      try {
        await apiClient.queries.create(values);
        setOpen(false);
        formik.resetForm();
        fetchQueries();
      } catch (error) {
        console.error('Error creating query:', error);
      }
    },
  });

  const handleDelete = async (queryId: number) => {
    try {
      await apiClient.queries.delete(queryId);
      fetchQueries();
    } catch (error) {
      console.error('Error deleting query:', error);
    }
  };

  const handleRerun = async (queryId: number) => {
    try {
      await apiClient.queries.rerun(queryId);
      fetchQueries();
    } catch (error) {
      console.error('Error rerunning query:', error);
    }
  };

  const getStatusColor = (status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    const colors: { [key: string]: 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' } = {
      pending: 'default',
      queued: 'info',
      running: 'primary',
      transferring: 'warning',
      completed: 'success',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Queries</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpen(true)}
        >
          New Query
        </Button>
      </Box>

      <Grid container spacing={2}>
        {queries.map((query) => (
          <Grid item xs={12} key={query.id}>
            <Card>
              <CardContent>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 2,
                  }}
                >
                  <Typography variant="h6">Query #{query.id}</Typography>
                  <Box>
                    <Chip
                      label={query.status}
                      color={getStatusColor(query.status)}
                      sx={{ mr: 1 }}
                    />
                    <IconButton
                      onClick={() => handleRerun(query.id)}
                      disabled={query.status === 'running'}
                    >
                      <RefreshIcon />
                    </IconButton>
                    <IconButton
                      onClick={() => handleDelete(query.id)}
                      disabled={query.status === 'running'}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    fontFamily: 'monospace',
                    bgcolor: 'grey.100',
                    p: 2,
                    borderRadius: 1,
                  }}
                >
                  {query.query_text}
                </Typography>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    mt: 2,
                  }}
                >
                  <Typography variant="body2" color="textSecondary">
                    Database: {query.db_tns}
                  </Typography>
                  <Typography variant="body2" color="textSecondary">
                    Created: {new Date(query.created_at).toLocaleString()}
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <form onSubmit={formik.handleSubmit}>
          <DialogTitle>New Query</DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              multiline
              rows={4}
              margin="normal"
              name="query_text"
              label="SQL Query"
              value={formik.values.query_text}
              onChange={formik.handleChange}
              error={
                formik.touched.query_text && Boolean(formik.errors.query_text)
              }
              helperText={formik.touched.query_text && formik.errors.query_text}
            />
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  margin="normal"
                  name="db_username"
                  label="Database Username"
                  value={formik.values.db_username}
                  onChange={formik.handleChange}
                  error={
                    formik.touched.db_username &&
                    Boolean(formik.errors.db_username)
                  }
                  helperText={
                    formik.touched.db_username && formik.errors.db_username
                  }
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  margin="normal"
                  name="db_password"
                  label="Database Password"
                  type="password"
                  value={formik.values.db_password}
                  onChange={formik.handleChange}
                  error={
                    formik.touched.db_password &&
                    Boolean(formik.errors.db_password)
                  }
                  helperText={
                    formik.touched.db_password && formik.errors.db_password
                  }
                />
              </Grid>
            </Grid>
            <TextField
              fullWidth
              margin="normal"
              name="db_tns"
              label="Database TNS"
              value={formik.values.db_tns}
              onChange={formik.handleChange}
              error={formik.touched.db_tns && Boolean(formik.errors.db_tns)}
              helperText={formik.touched.db_tns && formik.errors.db_tns}
            />
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  margin="normal"
                  name="export_location"
                  label="Export Location (Optional)"
                  value={formik.values.export_location}
                  onChange={formik.handleChange}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  margin="normal"
                  name="export_type"
                  label="Export Type (Optional)"
                  value={formik.values.export_type}
                  onChange={formik.handleChange}
                />
              </Grid>
            </Grid>
            <Grid container spacing={2}>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  margin="normal"
                  name="export_filename"
                  label="Export Filename (Optional)"
                  value={formik.values.export_filename}
                  onChange={formik.handleChange}
                />
              </Grid>
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  margin="normal"
                  name="ssh_hostname"
                  label="SSH Hostname (Optional)"
                  value={formik.values.ssh_hostname}
                  onChange={formik.handleChange}
                />
              </Grid>
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained">
              Create
            </Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
} 