-- Enable local users
ALTER SESSION SET "_ORACLE_SCRIPT"=true;

-- Simple health check query
SELECT 1 FROM DUAL;
EXIT; 