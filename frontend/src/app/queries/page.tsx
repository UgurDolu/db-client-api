'use client';

import React, { useEffect, useState, MouseEvent, ChangeEvent } from 'react';
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Paper,
  Tooltip,
  Divider,
  Checkbox,
  Fade,
  Alert,
  DialogContentText,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Close as CloseIcon,
  QueryStats as QueryIcon,
  Schedule as ScheduleIcon,
  Storage as StorageIcon,
  Code as CodeIcon,
  Info as InfoIcon,
  CloudDownload as ExportIcon,
  Computer as HostIcon,
  CalendarToday as DateIcon,
  Timer as TimerIcon,
  Update as UpdateIcon,
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Pending as PendingIcon,
  DataObject as MetadataIcon,
  PlaylistAddCheck as BatchIcon,
  Person as PersonIcon,
} from '@mui/icons-material';
import { useFormik } from 'formik';
import * as yup from 'yup';
import { apiClient, Query } from '../../service/api';

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

interface QueryDetailsModalProps {
  query: Query | null;
  open: boolean;
  onClose: () => void;
}

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

const getStatusIcon = (status: string) => {
  const icons = {
    pending: <PendingIcon />,
    queued: <ScheduleIcon />,
    running: <TimerIcon />,
    transferring: <ExportIcon />,
    completed: <CompletedIcon />,
    failed: <ErrorIcon />,
  };
  return icons[status as keyof typeof icons] || <WarningIcon />;
};

const QueryDetailsModal: React.FC<QueryDetailsModalProps> = ({ query, open, onClose }) => {
  if (!query) return null;

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
  };

  const formatValue = (key: string, value: any): string => {
    if (key === 'file_size') {
      const sizeInMB = (value / (1024 * 1024)).toFixed(2);
      return `${sizeInMB} MB`;
    }
    return Array.isArray(value) ? value.join(', ') : String(value);
  };

  const formatMetadata = (metadata: any) => {
    if (!metadata) return 'No metadata available';
    return (
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableBody>
            {Object.entries(metadata).map(([key, value]) => (
              <TableRow key={key}>
                <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                  {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}
                </TableCell>
                <TableCell>
                  {formatValue(key, value)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={1}>
            <QueryIcon color="primary" />
            <Typography variant="h6">Query Details #{query.id}</Typography>
          </Box>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <Divider />
      <DialogContent>
        <Box sx={{ mt: 2 }}>
          {/* SQL Query Section */}
          <Box sx={{ mb: 3 }}>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <CodeIcon color="primary" />
              <Typography variant="subtitle1">SQL Query</Typography>
            </Box>
            <Paper 
              variant="outlined" 
              sx={{ 
                p: 2,
                bgcolor: 'grey.50',
                borderRadius: 1,
              }}
            >
              <Typography
                variant="body2"
                sx={{
                  whiteSpace: 'pre-wrap',
                  fontFamily: 'monospace',
                }}
              >
                {query.query_text}
              </Typography>
            </Paper>
          </Box>

          {/* Database Information Section */}
          <Box sx={{ mb: 3 }}>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <StorageIcon color="primary" />
              <Typography variant="subtitle1">Database Information</Typography>
            </Box>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <StorageIcon fontSize="small" />
                        Database TNS
                      </Box>
                    </TableCell>
                    <TableCell>{query.db_tns}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <PersonIcon fontSize="small" />
                        Database Username
                      </Box>
                    </TableCell>
                    <TableCell>{query.db_username}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          {/* Status Information Section */}
          <Box sx={{ mb: 3 }}>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <InfoIcon color="primary" />
              <Typography variant="subtitle1">Status Information</Typography>
            </Box>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Chip
                  icon={getStatusIcon(query.status)}
                  label={query.status}
                  color={getStatusColor(query.status)}
                  sx={{ mb: 2 }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Box display="flex" alignItems="center" gap={1}>
                  <DateIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="textSecondary">Created: {formatDate(query.created_at)}</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Box display="flex" alignItems="center" gap={1}>
                  <TimerIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="textSecondary">Started: {formatDate(query.started_at)}</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Box display="flex" alignItems="center" gap={1}>
                  <UpdateIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="textSecondary">Updated: {formatDate(query.updated_at)}</Typography>
                </Box>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Box display="flex" alignItems="center" gap={1}>
                  <CompletedIcon fontSize="small" color="action" />
                  <Typography variant="body2" color="textSecondary">Completed: {formatDate(query.completed_at)}</Typography>
                </Box>
              </Grid>
            </Grid>

            {query.error_message && (
              <Box sx={{ mt: 2 }}>
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <ErrorIcon color="error" />
                  <Typography variant="subtitle1" color="error">Error Message</Typography>
                </Box>
                <Paper variant="outlined" sx={{ p: 2, bgcolor: '#fff5f5' }}>
                  <Typography variant="body2" color="error">{query.error_message}</Typography>
                </Paper>
              </Box>
            )}
          </Box>

          <Box sx={{ mt: 3 }}>
            <Box display="flex" alignItems="center" gap={1} mb={2}>
              <ExportIcon color="primary" />
              <Typography variant="subtitle1">Export Configuration</Typography>
            </Box>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <StorageIcon fontSize="small" />
                        Export Location
                      </Box>
                    </TableCell>
                    <TableCell>{query.export_location || 'N/A'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <CodeIcon fontSize="small" />
                        Export Type
                      </Box>
                    </TableCell>
                    <TableCell>{query.export_type || 'N/A'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <ExportIcon fontSize="small" />
                        Export Filename
                      </Box>
                    </TableCell>
                    <TableCell>{query.export_filename || 'N/A'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 'bold' }}>
                      <Box display="flex" alignItems="center" gap={1}>
                        <HostIcon fontSize="small" />
                        SSH Hostname
                      </Box>
                    </TableCell>
                    <TableCell>{query.ssh_hostname || 'N/A'}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </Box>

          {query.result_metadata && (
            <Box sx={{ mt: 3 }}>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <MetadataIcon color="primary" />
                <Typography variant="subtitle1">Result Metadata</Typography>
              </Box>
              {formatMetadata(query.result_metadata)}
            </Box>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} startIcon={<CloseIcon />}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default function QueriesPage() {
  const [queries, setQueries] = useState<Query[]>([]);
  const [open, setOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [selectedQuery, setSelectedQuery] = useState<Query | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedQueries, setSelectedQueries] = useState<number[]>([]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState<'rerun' | 'delete' | null>(null);

  const POLLING_INTERVAL = 2500; // 5 seconds
  const [lastQueryCount, setLastQueryCount] = useState<number>(0);

  const fetchQueries = async () => {
    try {
      const response = await apiClient.queries.list();
      setQueries(response.data);

      // Check for new queries
      if (response.data.length !== lastQueryCount) {
        setLastQueryCount(response.data.length);
      }

    } catch (error) {
      console.error('Error fetching queries:', error);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchQueries();
  }, []);

  // Always keep polling active
  useEffect(() => {
    const intervalId = window.setInterval(fetchQueries, POLLING_INTERVAL);

    // Cleanup function
    return () => {
      window.clearInterval(intervalId);
    };
  }, []); // Empty dependency array to keep polling always active

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

  const handleQueryClick = (query: Query) => {
    setSelectedQuery(query);
    setDetailsOpen(true);
  };

  const handleSelectQuery = (queryId: number, event: MouseEvent | ChangeEvent) => {
    event.stopPropagation();
    setSelectedQueries(prev => {
      if (prev.includes(queryId)) {
        return prev.filter(id => id !== queryId);
      }
      return [...prev, queryId];
    });
  };

  const handleSelectAll = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedQueries(queries.map(query => query.id));
    } else {
      setSelectedQueries([]);
    }
  };

  const handleBatchAction = (action: 'rerun' | 'delete') => {
    setConfirmAction(action);
    setConfirmDialogOpen(true);
  };

  const handleConfirmBatchAction = async () => {
    try {
      if (confirmAction === 'rerun') {
        await apiClient.queries.batchRerun(selectedQueries);
      } else if (confirmAction === 'delete') {
        await apiClient.queries.batchDelete(selectedQueries);
      }
      setSelectedQueries([]);
      fetchQueries();
    } catch (error) {
      console.error(`Error performing batch ${confirmAction}:`, error);
    } finally {
      setConfirmDialogOpen(false);
      setConfirmAction(null);
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box display="flex" alignItems="center" gap={1}>
          <QueryIcon color="primary" fontSize="large" />
          <Typography variant="h4">Queries</Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setOpen(true)}
          sx={{ borderRadius: 2 }}
        >
          New Query
        </Button>
      </Box>

      {/* Batch Actions Toolbar */}
      <Fade in={selectedQueries.length > 0}>
        <Paper 
          sx={{ 
            mb: 2, 
            p: 2, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
          }}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <BatchIcon />
            <Typography>
              {selectedQueries.length} {selectedQueries.length === 1 ? 'query' : 'queries'} selected
            </Typography>
          </Box>
          <Box display="flex" gap={1}>
            <Tooltip title="Rerun Selected">
              <Button
                variant="contained"
                color="inherit"
                startIcon={<RefreshIcon />}
                onClick={() => handleBatchAction('rerun')}
                sx={{ color: 'primary.main' }}
              >
                Rerun
              </Button>
            </Tooltip>
            <Tooltip title="Delete Selected">
              <Button
                variant="contained"
                color="error"
                startIcon={<DeleteIcon />}
                onClick={() => handleBatchAction('delete')}
              >
                Delete
              </Button>
            </Tooltip>
          </Box>
        </Paper>
      </Fade>

      <Grid container spacing={2}>
        {queries.map((query) => (
          <Grid item xs={12} key={query.id}>
            <Card 
              sx={{ 
                cursor: 'pointer',
                '&:hover': {
                  boxShadow: 6,
                  transform: 'translateY(-2px)',
                },
                transition: 'all 0.2s ease-in-out',
                position: 'relative',
              }}
              onClick={() => handleQueryClick(query)}
            >
              <Box
                sx={{
                  position: 'absolute',
                  left: 1,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  zIndex: 1,
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <Checkbox
                  checked={selectedQueries.includes(query.id)}
                  onChange={(e) => handleSelectQuery(query.id, e)}
                  sx={{ ml: 1 }}
                />
              </Box>
              <CardContent sx={{ pl: 7 }}>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 2,
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1}>
                    <QueryIcon color="primary" />
                    <Typography variant="h6">Query #{query.id}</Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Chip
                      icon={getStatusIcon(query.status)}
                      label={query.status}
                      color={getStatusColor(query.status)}
                      sx={{ mr: 1 }}
                    />
                    <Tooltip title="Rerun Query">
                      <IconButton
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRerun(query.id);
                        }}
                        disabled={query.status === 'running'}
                        size="small"
                      >
                        <RefreshIcon />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete Query">
                      <IconButton
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(query.id);
                        }}
                        disabled={query.status === 'running'}
                        size="small"
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </Box>
                <Paper 
                  variant="outlined" 
                  sx={{ 
                    p: 2, 
                    mb: 2,
                    bgcolor: 'grey.50',
                    borderRadius: 1,
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'monospace',
                    }}
                  >
                    {query.query_text}
                  </Typography>
                </Paper>
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1}>
                    <StorageIcon fontSize="small" color="action" />
                    <Typography variant="body2" color="textSecondary">
                      Database: {query.db_tns}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <DateIcon fontSize="small" color="action" />
                    <Typography variant="body2" color="textSecondary">
                      Created: {new Date(query.created_at).toLocaleString()}
                    </Typography>
                  </Box>
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

      <QueryDetailsModal
        query={selectedQuery}
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
      />

      {/* Confirmation Dialog */}
      <Dialog
        open={confirmDialogOpen}
        onClose={() => setConfirmDialogOpen(false)}
      >
        <DialogTitle>
          Confirm Batch {confirmAction === 'rerun' ? 'Rerun' : 'Delete'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to {confirmAction === 'rerun' ? 'rerun' : 'delete'} {selectedQueries.length} selected {selectedQueries.length === 1 ? 'query' : 'queries'}?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleConfirmBatchAction} 
            variant="contained" 
            color={confirmAction === 'delete' ? 'error' : 'primary'}
            autoFocus
          >
            {confirmAction === 'rerun' ? 'Rerun' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
} 