import { AppBar, Toolbar, Button, Box, IconButton, Typography } from '@mui/material';
import { Settings as SettingsIcon, Logout as LogoutIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export default function NavigationBar() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
  };

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography
          variant="h6"
          component="div"
          sx={{ flexGrow: 1, cursor: 'pointer' }}
          onClick={() => navigate('/')}
        >
          DB Client
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <IconButton
            color="inherit"
            onClick={() => navigate('/settings')}
            title="Settings"
          >
            <SettingsIcon />
          </IconButton>
          <IconButton
            color="inherit"
            onClick={handleLogout}
            title="Logout"
          >
            <LogoutIcon />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
} 