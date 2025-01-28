import { useState } from 'react';
import {
  Container,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Box,
  Chip,
  TablePagination,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  LinearProgress,
  Card,
  CardContent,
  Grid,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  TableSortLabel,
  Checkbox,
  Menu,
} from '@mui/material';
import { 
  Add as AddIcon, 
  Refresh as RefreshIcon,
  AccessTime as PendingIcon,
  PlayArrow as RunningIcon,
  Check as CompletedIcon,
  Error as ErrorIcon,
  Queue as QueuedIcon,
  Download as DownloadIcon,
  FilterList as FilterIcon,
  Delete as DeleteIcon,
  PlayArrow as RunIcon,
  Upload as TransferringIcon,
} from '@mui/icons-material';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { logger } from '../services/logger';

interface Query {
  id: number;
  query_text: string;
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  result_metadata: any;
  export_type?: string;
  export_location?: string;
}

interface NewQuery {
  db_username: string;
  db_password: string;
  db_tns: string;
  query_text: string;
}

interface QueryDetails {
  timing: {
    total_duration: string;
    queue_duration: string;
    execution_duration: string;
  };
  metadata: {
    rows_affected?: number;
    file_size?: string;
    column_count?: number;
  };
}

interface SortConfig {
  field: keyof Query | '';
  direction: 'asc' | 'desc';
}

interface FilterConfig {
  status: string[];
  dateRange: {
    start: string;
    end: string;
  };
  searchText: string;
}

interface BatchOperationResponse {
  message: string;
  successful_ids: number[];
  failed_ids?: Record<number, string>;
}

const initialNewQuery: NewQuery = {
  db_username: '',
  db_password: '',
  db_tns: '',
  query_text: '',
};

const getStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed':
      return <CompletedIcon fontSize="small" />;
    case 'failed':
      return <ErrorIcon fontSize="small" />;
    case 'running':
      return <RunningIcon fontSize="small" />;
    case 'pending':
      return <PendingIcon fontSize="small" />;
    case 'queued':
      return <QueuedIcon fontSize="small" />;
    case 'transferring':
      return <TransferringIcon fontSize="small" />;
    default:
      return <QueuedIcon fontSize="small" />;
  }
};

const getStatusText = (status: string) => {
  switch (status.toLowerCase()) {
    case 'completed':
      return 'Query completed successfully';
    case 'failed':
      return 'Query failed';
    case 'running':
      return 'Query is currently running';
    case 'pending':
      return 'Query is pending execution';
    case 'queued':
      return 'Query is queued for execution';
    case 'transferring':
      return 'Transferring results to destination';
    default:
      return status;
  }
};

const formatFileSize = (bytes: number): string => {
  if (!bytes) return '0 MB';
  const mb = bytes / (1024 * 1024);
  return `${mb.toFixed(2)} MB`;
};

export default function QueriesPage() {
  const { logout } = useAuth();
  const queryClient = useQueryClient();
  const [selectedQuery, setSelectedQuery] = useState<Query | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [newQuery, setNewQuery] = useState<NewQuery>(initialNewQuery);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [isManualRefetching, setIsManualRefetching] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [sort, setSort] = useState<SortConfig>({ field: '', direction: 'desc' });
  const [filters, setFilters] = useState<FilterConfig>({
    status: [],
    dateRange: {
      start: '',
      end: '',
    },
    searchText: '',
  });
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false);
  const [selectedQueries, setSelectedQueries] = useState<number[]>([]);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const { data: queries, isLoading, refetch } = useQuery({
    queryKey: ['queries'],
    queryFn: async () => {
      logger.debug('Fetching queries');
      try {
        const response = await axios.get<Query[]>('http://localhost:8000/api/queries/', {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        });
        logger.info('Queries fetched successfully', {
          count: response.data.length,
          statuses: response.data.map(q => q.status),
        });
        return response.data;
      } catch (error) {
        logger.error('Failed to fetch queries', error);
        throw error;
      }
    },
    refetchInterval: (query) => {
      const data = query.state.data as Query[] | undefined;
      if (!data) return 3000; // If no data yet, poll quickly
      
      // Check for active queries
      const hasActiveQueries = data.some(
        (query: Query) => ['PENDING', 'QUEUED', 'RUNNING'].includes(query.status.toUpperCase())
      );

      // If there are active queries, poll every 2 seconds
      // If no active queries but auto-refresh enabled, poll every 30 seconds
      // If manual refresh only, stop polling
      return hasActiveQueries ? 2000 : 30000;
    },
    // Enable background polling when tab is not focused
    refetchIntervalInBackground: true,
    // Always refetch on window focus
    refetchOnWindowFocus: true,
    // Retry failed requests
    retry: 3,
    retryDelay: 1000,
    // Keep previous results while fetching
    gcTime: 5 * 60 * 1000, // 5 minutes
  });

  // Poll stats separately for active queries
  const { data: stats } = useQuery({
    queryKey: ['query-stats'],
    queryFn: async () => {
      try {
        const response = await axios.get<{ running_queries: number; queued_queries: number }>(
          'http://localhost:8000/api/queries/stats/current',
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('token')}`,
            },
          }
        );
        return response.data;
      } catch (error) {
        logger.error('Failed to fetch query stats', error);
        throw error;
      }
    },
    refetchInterval: 2000, // Poll every 2 seconds
    refetchIntervalInBackground: true,
    enabled: queries?.some(
      (query: Query) => ['PENDING', 'QUEUED', 'RUNNING'].includes(query.status.toUpperCase())
    ) ?? false,
  });

  // Add visual indicator for active queries
  const hasActiveQueries = queries?.some(
    (query: Query) => ['PENDING', 'QUEUED', 'RUNNING'].includes(query.status.toUpperCase())
  ) ?? false;

  const handleManualRefresh = async () => {
    setIsManualRefetching(true);
    try {
      await refetch();
    } finally {
      setIsManualRefetching(false);
    }
  };

  const handleCreateQuery = async () => {
    setError('');
    setIsSubmitting(true);
    logger.debug('Creating new query', { ...newQuery, db_password: '[REDACTED]' });

    try {
      await axios.post(
        'http://localhost:8000/api/queries/',
        newQuery,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json',
          },
        }
      );
      logger.info('Query created successfully');
      setIsCreateModalOpen(false);
      setNewQuery(initialNewQuery);
      await refetch();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to create query';
      logger.error('Failed to create query', { error: errorMessage });
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setNewQuery(prev => ({
      ...prev,
      [name]: value
    }));
    if (error) setError('');
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'primary';
      case 'pending':
      case 'queued':
        return 'warning';
      case 'transferring':
        return 'info';
      default:
        return 'default';
    }
  };

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  const handleDownload = (query: Query) => {
    logger.debug('Initiating download', { queryId: query.id });
    try {
      window.open(
        `http://localhost:8000/api/queries/${query.id}/download`,
        '_blank'
      );
      logger.info('Download initiated', { queryId: query.id });
    } catch (error) {
      logger.error('Failed to initiate download', { queryId: query.id, error });
    }
  };

  const handleLogout = () => {
    logger.info('User initiated logout');
    logout();
  };

  const handleChangePage = (event: unknown, newPage: number) => {
    logger.debug('Changing page', { from: page, to: newPage });
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newRowsPerPage = parseInt(event.target.value, 10);
    logger.debug('Changing rows per page', { from: rowsPerPage, to: newRowsPerPage });
    setRowsPerPage(newRowsPerPage);
    setPage(0);
  };

  const handleSort = (field: keyof Query) => {
    setSort(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const handleStatusFilterChange = (event: SelectChangeEvent<string[]>) => {
    setFilters(prev => ({
      ...prev,
      status: event.target.value as string[]
    }));
    setPage(0);
  };

  const handleDateRangeChange = (field: 'start' | 'end') => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilters(prev => ({
      ...prev,
      dateRange: {
        ...prev.dateRange,
        [field]: event.target.value
      }
    }));
    setPage(0);
  };

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilters(prev => ({
      ...prev,
      searchText: event.target.value
    }));
    setPage(0);
  };

  const filteredAndSortedQueries = queries?.filter(query => {
    if (filters.status.length > 0 && !filters.status.includes(query.status.toLowerCase())) {
      return false;
    }

    if (filters.dateRange.start && new Date(query.created_at) < new Date(filters.dateRange.start)) {
      return false;
    }
    if (filters.dateRange.end && new Date(query.created_at) > new Date(filters.dateRange.end)) {
      return false;
    }

    if (filters.searchText) {
      const searchLower = filters.searchText.toLowerCase();
      return (
        query.query_text.toLowerCase().includes(searchLower) ||
        query.id.toString().includes(searchLower)
      );
    }

    return true;
  }).sort((a, b) => {
    if (!sort.field) return 0;
    
    const aValue = a[sort.field];
    const bValue = b[sort.field];
    
    if (aValue === null) return 1;
    if (bValue === null) return -1;
    
    const comparison = aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
    return sort.direction === 'asc' ? comparison : -comparison;
  });

  const paginatedQueries = filteredAndSortedQueries?.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const calculateQueryDurations = (query: Query): QueryDetails => {
    const timing = {
      total_duration: '-',
      queue_duration: '-',
      execution_duration: '-'
    };
    
    if (query.completed_at && query.created_at) {
      const total = new Date(query.completed_at).getTime() - new Date(query.created_at).getTime();
      timing.total_duration = `${(total / 1000).toFixed(2)}s`;
    }
    
    if (query.started_at && query.created_at) {
      const queue = new Date(query.started_at).getTime() - new Date(query.created_at).getTime();
      timing.queue_duration = `${(queue / 1000).toFixed(2)}s`;
    }
    
    if (query.completed_at && query.started_at) {
      const execution = new Date(query.completed_at).getTime() - new Date(query.started_at).getTime();
      timing.execution_duration = `${(execution / 1000).toFixed(2)}s`;
    }

    const metadata = {
      rows_affected: query.result_metadata?.rows_affected || 0,
      file_size: query.result_metadata?.file_size || '0 KB',
      column_count: query.result_metadata?.column_count || 0
    };

    return { timing, metadata };
  };

  const handleRowClick = (query: Query) => {
    setSelectedQuery(query);
    setDetailsOpen(true);
  };

  const handleSelectQuery = (queryId: number) => {
    setSelectedQueries(prev => {
      if (prev.includes(queryId)) {
        return prev.filter(id => id !== queryId);
      }
      return [...prev, queryId];
    });
  };

  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedQueries(filteredAndSortedQueries?.map(q => q.id) || []);
    } else {
      setSelectedQueries([]);
    }
  };

  const handleBatchRerun = async () => {
    setError('');
    logger.info('Rerunning selected queries', { queryIds: selectedQueries });
    
    try {
      const response = await axios.post<BatchOperationResponse>(
        'http://localhost:8000/api/queries/batch/rerun',
        {
          query_ids: selectedQueries
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
        }
      );
      
      logger.info('Successfully rerun queries', response.data);
      
      // Show success/failure information
      if (response.data.failed_ids && Object.keys(response.data.failed_ids).length > 0) {
        const failedIds = Object.entries(response.data.failed_ids)
          .map(([id, reason]) => `ID ${id} (${reason})`)
          .join(', ');
        setError(`Some queries failed to rerun: ${failedIds}`);
      }
      
      await refetch();
      setSelectedQueries([]);
    } catch (error: any) {
      logger.error('Failed to rerun queries', error);
      const errorMessage = error.response?.data?.detail || 'Failed to rerun selected queries';
      setError(errorMessage);
    }
  };

  const handleBatchDelete = async () => {
    setError('');
    logger.info('Deleting selected queries', { queryIds: selectedQueries });
    
    try {
      const response = await axios.post(
        'http://localhost:8000/api/queries/batch/delete',
        {
          query_ids: selectedQueries
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
          },
        }
      );
      
      logger.info('Successfully deleted queries', response.data);
      await refetch();
      setSelectedQueries([]);
    } catch (error: any) {
      logger.error('Failed to delete queries', error);
      const errorMessage = error.response?.data?.detail || 'Failed to delete selected queries';
      setError(errorMessage);
    }
  };

  const handleRerunSingle = async (queryId: number, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent row click
    setError('');
    logger.info('Rerunning query', { queryId });
    
    try {
      await axios.post(
        `http://localhost:8000/api/queries/${queryId}/rerun`,
        {},
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );
      
      logger.info('Successfully rerun query');
      await refetch();
    } catch (error) {
      logger.error('Failed to rerun query', error);
      setError('Failed to rerun query');
    }
  };

  const handleDeleteSingle = async (queryId: number, event: React.MouseEvent) => {
    event.stopPropagation(); // Prevent row click
    setError('');
    logger.info('Deleting query', { queryId });
    
    try {
      await axios.delete(
        `http://localhost:8000/api/queries/${queryId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );
      
      logger.info('Successfully deleted query');
      await refetch();
    } catch (error) {
      logger.error('Failed to delete query', error);
      setError('Failed to delete query');
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4" component="h1">
            My Queries
          </Typography>
          <Tooltip title="Refresh queries">
            <IconButton 
              onClick={handleManualRefresh} 
              disabled={isLoading || isManualRefetching}
              size="small"
              color={hasActiveQueries ? "primary" : "default"}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
          {(isLoading || isManualRefetching) && (
            <CircularProgress size={20} />
          )}
          {stats && (hasActiveQueries || stats.running_queries > 0 || stats.queued_queries > 0) && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {stats.running_queries > 0 && (
                <Chip
                  size="small"
                  icon={<RunningIcon />}
                  label={`${stats.running_queries} Running`}
                  color="primary"
                />
              )}
              {stats.queued_queries > 0 && (
                <Chip
                  size="small"
                  icon={<QueuedIcon />}
                  label={`${stats.queued_queries} Queued`}
                  color="warning"
                />
              )}
            </Box>
          )}
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          {selectedQueries.length > 0 && (
            <>
              <Button
                variant="outlined"
                startIcon={<RunIcon />}
                onClick={handleBatchRerun}
              >
                Rerun Selected ({selectedQueries.length})
              </Button>
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteIcon />}
                onClick={handleBatchDelete}
              >
                Delete Selected ({selectedQueries.length})
              </Button>
            </>
          )}
          <Button
            variant="outlined"
            startIcon={<FilterIcon />}
            onClick={() => setIsFilterDrawerOpen(true)}
          >
            Filters
          </Button>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setIsCreateModalOpen(true)}
          >
            New Query
          </Button>
          <Button variant="outlined" color="primary" onClick={handleLogout}>
            Logout
          </Button>
        </Box>
      </Box>

      {/* Filter Dialog */}
      <Dialog
        open={isFilterDrawerOpen}
        onClose={() => setIsFilterDrawerOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Filter Queries</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <TextField
              fullWidth
              label="Search"
              value={filters.searchText}
              onChange={handleSearchChange}
              placeholder="Search by query text or ID"
            />
            
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                multiple
                value={filters.status}
                onChange={handleStatusFilterChange}
                label="Status"
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {(selected as string[]).map((value) => (
                      <Chip
                        key={value}
                        label={value}
                        size="small"
                        icon={getStatusIcon(value)}
                        color={getStatusColor(value) as any}
                      />
                    ))}
                  </Box>
                )}
              >
                {['completed', 'failed', 'running', 'pending', 'queued', 'transferring'].map((status) => (
                  <MenuItem key={status} value={status}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getStatusIcon(status)}
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                type="datetime-local"
                label="Start Date"
                value={filters.dateRange.start}
                onChange={handleDateRangeChange('start')}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
              <TextField
                type="datetime-local"
                label="End Date"
                value={filters.dateRange.end}
                onChange={handleDateRangeChange('end')}
                InputLabelProps={{ shrink: true }}
                fullWidth
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => {
              setFilters({
                status: [],
                dateRange: { start: '', end: '' },
                searchText: ''
              });
              setPage(0);
            }}
          >
            Clear All
          </Button>
          <Button onClick={() => setIsFilterDrawerOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      <Paper>
        {(isLoading || isManualRefetching || hasActiveQueries) && (
          <LinearProgress sx={{ borderTopLeftRadius: 4, borderTopRightRadius: 4 }} />
        )}
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    indeterminate={
                      selectedQueries.length > 0 &&
                      selectedQueries.length < (filteredAndSortedQueries?.length || 0)
                    }
                    checked={
                      (filteredAndSortedQueries?.length || 0) > 0 &&
                      selectedQueries.length === (filteredAndSortedQueries?.length || 0)
                    }
                    onChange={handleSelectAll}
                  />
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort.field === 'id'}
                    direction={sort.direction}
                    onClick={() => handleSort('id')}
                  >
                    ID
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort.field === 'query_text'}
                    direction={sort.direction}
                    onClick={() => handleSort('query_text')}
                  >
                    Query
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort.field === 'status'}
                    direction={sort.direction}
                    onClick={() => handleSort('status')}
                  >
                    Status
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort.field === 'created_at'}
                    direction={sort.direction}
                    onClick={() => handleSort('created_at')}
                  >
                    Created At
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort.field === 'started_at'}
                    direction={sort.direction}
                    onClick={() => handleSort('started_at')}
                  >
                    Started At
                  </TableSortLabel>
                </TableCell>
                <TableCell>
                  <TableSortLabel
                    active={sort.field === 'completed_at'}
                    direction={sort.direction}
                    onClick={() => handleSort('completed_at')}
                  >
                    Completed At
                  </TableSortLabel>
                </TableCell>
                <TableCell>Results</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                      <CircularProgress size={40} />
                      <Typography color="text.secondary">
                        Loading queries...
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ) : queries?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                      <Typography color="text.secondary">
                        No queries found
                      </Typography>
                      <Button
                        variant="outlined"
                        startIcon={<AddIcon />}
                        onClick={() => setIsCreateModalOpen(true)}
                      >
                        Create your first query
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ) : paginatedQueries?.map((query) => (
                <TableRow 
                  key={query.id}
                  onClick={() => handleRowClick(query)}
                  sx={{
                    backgroundColor: query.status.toLowerCase() === 'failed' ? 'error.main' : undefined,
                    '&:hover': {
                      backgroundColor: query.status.toLowerCase() === 'failed' 
                        ? 'error.dark' 
                        : 'action.hover',
                      cursor: 'pointer',
                    },
                  }}
                >
                  <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={selectedQueries.includes(query.id)}
                      onChange={() => handleSelectQuery(query.id)}
                    />
                  </TableCell>
                  <TableCell>{query.id}</TableCell>
                  <TableCell>
                    <Tooltip title={query.query_text}>
                      <Typography
                        sx={{
                          maxWidth: 300,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          cursor: 'help',
                        }}
                      >
                        {query.query_text}
                      </Typography>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <Tooltip title={getStatusText(query.status)}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Chip
                          icon={getStatusIcon(query.status)}
                          label={query.status}
                          color={getStatusColor(query.status) as any}
                          size="small"
                          sx={{ minWidth: 100 }}
                        />
                        {['PENDING', 'QUEUED', 'RUNNING', 'TRANSFERRING'].includes(query.status.toUpperCase()) && (
                          <CircularProgress size={16} />
                        )}
                      </Box>
                    </Tooltip>
                  </TableCell>
                  <TableCell>{formatDateTime(query.created_at)}</TableCell>
                  <TableCell>{formatDateTime(query.started_at)}</TableCell>
                  <TableCell>{formatDateTime(query.completed_at)}</TableCell>
                  <TableCell>
                    {query.status === 'COMPLETED' && query.result_metadata?.file_path && (
                      <Button
                        variant="text"
                        size="small"
                        startIcon={<DownloadIcon />}
                        onClick={() => handleDownload(query)}
                      >
                        Download
                      </Button>
                    )}
                    {query.status === 'FAILED' && (
                      <Tooltip title={query.error_message}>
                        <Typography 
                          color="error" 
                          variant="caption"
                          sx={{ 
                            cursor: 'help',
                            display: 'flex',
                            alignItems: 'center',
                            gap: 0.5,
                          }}
                        >
                          <ErrorIcon fontSize="small" />
                          {query.error_message}
                        </Typography>
                      </Tooltip>
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Tooltip title="Rerun query">
                        <IconButton
                          size="small"
                          onClick={(e) => handleRerunSingle(query.id, e)}
                          disabled={['RUNNING', 'QUEUED'].includes(query.status)}
                        >
                          <RunIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete query">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={(e) => handleDeleteSingle(query.id, e)}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {filteredAndSortedQueries?.length || 0} queries found
          </Typography>
          <TablePagination
            component="div"
            count={filteredAndSortedQueries?.length || 0}
            page={page}
            onPageChange={handleChangePage}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={handleChangeRowsPerPage}
            rowsPerPageOptions={[5, 10, 25, 50]}
          />
        </Box>
      </Paper>

      {/* Create Query Modal */}
      <Dialog 
        open={isCreateModalOpen} 
        onClose={() => !isSubmitting && setIsCreateModalOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Create New Query</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2, mt: 1 }}>
              {error}
            </Alert>
          )}
          <TextField
            margin="normal"
            required
            fullWidth
            label="Database Username"
            name="db_username"
            value={newQuery.db_username}
            onChange={handleInputChange}
            disabled={isSubmitting}
          />
          <TextField
            margin="normal"
            required
            fullWidth
            label="Database Password"
            name="db_password"
            type="password"
            value={newQuery.db_password}
            onChange={handleInputChange}
            disabled={isSubmitting}
          />
          <TextField
            margin="normal"
            required
            fullWidth
            label="Database TNS"
            name="db_tns"
            value={newQuery.db_tns}
            onChange={handleInputChange}
            disabled={isSubmitting}
            placeholder="localhost:1521/XE"
          />
          <TextField
            margin="normal"
            required
            fullWidth
            label="SQL Query"
            name="query_text"
            value={newQuery.query_text}
            onChange={handleInputChange}
            disabled={isSubmitting}
            multiline
            rows={4}
            placeholder="SELECT * FROM table WHERE condition"
          />
        </DialogContent>
        <DialogActions sx={{ p: 3 }}>
          <Button 
            onClick={() => setIsCreateModalOpen(false)} 
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            onClick={handleCreateQuery}
            variant="contained"
            disabled={isSubmitting || !newQuery.db_username || !newQuery.db_password || !newQuery.db_tns || !newQuery.query_text}
          >
            {isSubmitting ? <CircularProgress size={24} /> : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Query Details Dialog */}
      <Dialog
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedQuery && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6">
                  Query #{selectedQuery.id}
                </Typography>
                <Chip
                  icon={getStatusIcon(selectedQuery.status)}
                  label={selectedQuery.status}
                  color={getStatusColor(selectedQuery.status) as any}
                  size="small"
                />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={3}>
                {/* Query Text Section */}
                <Grid item xs={12}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        SQL Query
                      </Typography>
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'monospace',
                          bgcolor: 'grey.100',
                          p: 2,
                          borderRadius: 1
                        }}
                      >
                        {selectedQuery.query_text}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Timing Information */}
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        Timing Information
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {Object.entries(calculateQueryDurations(selectedQuery).timing).map(([key, value]) => (
                          <Box key={key} sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2" color="text.secondary">
                              {key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}:
                            </Typography>
                            <Typography variant="body2">
                              {value || '-'}
                            </Typography>
                          </Box>
                        ))}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Result Information */}
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        Result Information
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">
                            Row Count:
                          </Typography>
                          <Typography variant="body2">
                            {selectedQuery.result_metadata?.rows || 0}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">
                            Column Count:
                          </Typography>
                          <Typography variant="body2">
                            {selectedQuery.result_metadata?.columns || 0}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">
                            File Size:
                          </Typography>
                          <Typography variant="body2">
                            {formatFileSize(selectedQuery.result_metadata?.file_size || 0)}
                          </Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Export Information */}
                <Grid item xs={12} md={6}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        Export Information
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">
                            Export Type:
                          </Typography>
                          <Typography variant="body2">
                            {selectedQuery.export_type?.toUpperCase() || 'Default (CSV)'}
                          </Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">
                            Export Location:
                          </Typography>
                          <Tooltip title={selectedQuery.export_location || 'Default Location'}>
                            <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                              {selectedQuery.export_location || 'Default Location'}
                            </Typography>
                          </Tooltip>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Timestamps */}
                <Grid item xs={12}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        Timeline
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">Created:</Typography>
                          <Typography variant="body2">{formatDateTime(selectedQuery.created_at)}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">Started:</Typography>
                          <Typography variant="body2">{formatDateTime(selectedQuery.started_at)}</Typography>
                        </Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                          <Typography variant="body2" color="text.secondary">Completed:</Typography>
                          <Typography variant="body2">{formatDateTime(selectedQuery.completed_at)}</Typography>
                        </Box>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Error Message (if any) */}
                {selectedQuery.error_message && (
                  <Grid item xs={12}>
                    <Alert severity="error" sx={{ mt: 2 }}>
                      <Typography variant="subtitle2">Error Message:</Typography>
                      <Typography variant="body2">{selectedQuery.error_message}</Typography>
                    </Alert>
                  </Grid>
                )}
              </Grid>
            </DialogContent>
            <DialogActions>
              {selectedQuery.status === 'COMPLETED' && selectedQuery.result_metadata?.file_path && (
                <Button
                  startIcon={<DownloadIcon />}
                  onClick={() => handleDownload(selectedQuery)}
                  color="primary"
                >
                  Download Results
                </Button>
              )}
              <Button onClick={() => setDetailsOpen(false)}>Close</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Container>
  );
} 