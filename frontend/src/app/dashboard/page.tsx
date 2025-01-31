'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  CircularProgress,
  Paper,
  Chip,
  Tooltip,
  IconButton,
  Divider,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  QueryStats as QueryIcon,
  Schedule as QueueIcon,
  PlayArrow as RunningIcon,
  History as RecentIcon,
  CalendarToday as DateIcon,
  Timer as TimerIcon,
  Storage as DatabaseIcon,
  Pending as PendingIcon,
  Send as TransferIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { apiClient, Query } from '../../service/api';

interface QueryStats {
  running_queries: number;
  queued_queries: number;
  pending_queries: number;
  transferring_queries: number;
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
    pending: <TimerIcon />,
    queued: <QueueIcon />,
    running: <RunningIcon />,
    completed: <QueryIcon />,
    failed: <QueryIcon />,
  };
  return icons[status as keyof typeof icons] || <QueryIcon />;
};

export default function DashboardPage() {
  const [stats, setStats] = useState<QueryStats | null>(null);
  const [recentQueries, setRecentQueries] = useState<Query[]>([]);
  const [loading, setLoading] = useState(true);

  const POLLING_INTERVAL = 2500; // 2.5 seconds

  const fetchData = async () => {
    try {
      const [statsResponse, queriesResponse] = await Promise.all([
        apiClient.queries.getCurrentStats(),
        apiClient.queries.list(),
      ]);

      setStats(statsResponse.data);
      setRecentQueries(queriesResponse.data.slice(0, 5)); // Show only 5 most recent queries
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, []);

  // Set up polling
  useEffect(() => {
    const intervalId = window.setInterval(fetchData, POLLING_INTERVAL);

    // Cleanup function
    return () => {
      window.clearInterval(intervalId);
    };
  }, []); // Empty dependency array to keep polling always active

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
          <DashboardIcon color="primary" fontSize="large" />
          <Typography variant="h4">Dashboard</Typography>
        </Box>
        <Tooltip title="Refresh Dashboard">
          <IconButton 
            onClick={fetchData}
            sx={{ 
              transition: 'transform 0.2s',
              '&:hover': { transform: 'rotate(180deg)' }
            }}
          >
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={3}>
          <Card 
            sx={{ 
              height: '100%',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 3,
              },
            }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <RunningIcon color="primary" />
                <Typography color="textSecondary">Running Queries</Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
              <Typography variant="h3" sx={{ mt: 2, color: 'primary.main' }}>
                {stats?.running_queries || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card 
            sx={{ 
              height: '100%',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 3,
              },
            }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <QueueIcon color="info" />
                <Typography color="textSecondary">Queued Queries</Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
              <Typography variant="h3" sx={{ mt: 2, color: 'info.main' }}>
                {stats?.queued_queries || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card 
            sx={{ 
              height: '100%',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 3,
              },
            }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <PendingIcon color="warning" />
                <Typography color="textSecondary">Pending Queries</Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
              <Typography variant="h3" sx={{ mt: 2, color: 'warning.main' }}>
                {stats?.pending_queries || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card 
            sx={{ 
              height: '100%',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: 3,
              },
            }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={1} mb={2}>
                <TransferIcon color="secondary" />
                <Typography color="textSecondary">Transferring Queries</Typography>
              </Box>
              <Divider sx={{ my: 1 }} />
              <Typography variant="h3" sx={{ mt: 2, color: 'secondary.main' }}>
                {stats?.transferring_queries || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Queries */}
        <Grid item xs={12}>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <RecentIcon color="primary" />
            <Typography variant="h5">Recent Queries</Typography>
          </Box>
          <Grid container spacing={2}>
            {recentQueries.map((query) => (
              <Grid item xs={12} key={query.id}>
                <Card 
                  sx={{ 
                    cursor: 'pointer',
                    '&:hover': {
                      transform: 'translateY(-2px)',
                      boxShadow: 3,
                    },
                    transition: 'all 0.2s ease-in-out',
                  }}
                >
                  <CardContent>
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
                      <Chip
                        icon={getStatusIcon(query.status)}
                        label={query.status}
                        color={getStatusColor(query.status)}
                        size="small"
                      />
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
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
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
                        <DatabaseIcon fontSize="small" color="action" />
                        <Typography variant="body2" color="textSecondary">
                          {query.db_tns}
                        </Typography>
                      </Box>
                      <Box display="flex" alignItems="center" gap={1}>
                        <DateIcon fontSize="small" color="action" />
                        <Typography variant="body2" color="textSecondary">
                          {new Date(query.created_at).toLocaleString()}
                        </Typography>
                      </Box>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
} 