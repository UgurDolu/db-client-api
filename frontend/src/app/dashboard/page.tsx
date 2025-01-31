'use client';

import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  CircularProgress,
} from '@mui/material';
import { apiClient, Query } from '../../lib/api';

interface QueryStats {
  running_queries: number;
  queued_queries: number;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<QueryStats | null>(null);
  const [recentQueries, setRecentQueries] = useState<Query[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
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

    fetchData();
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
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Stats Cards */}
        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Running Queries
              </Typography>
              <Typography variant="h3">
                {stats?.running_queries || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Queued Queries
              </Typography>
              <Typography variant="h3">
                {stats?.queued_queries || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Queries */}
        <Grid item xs={12}>
          <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
            Recent Queries
          </Typography>
          <Grid container spacing={2}>
            {recentQueries.map((query) => (
              <Grid item xs={12} key={query.id}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Query #{query.id}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="textSecondary"
                      sx={{
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
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
                      <Typography variant="body2">
                        Status: {query.status}
                      </Typography>
                      <Typography variant="body2">
                        Created:{' '}
                        {new Date(query.created_at).toLocaleDateString()}
                      </Typography>
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