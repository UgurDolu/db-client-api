-- Enable local users
ALTER SESSION SET "_ORACLE_SCRIPT"=true;

-- Create example schema
CREATE USER example IDENTIFIED BY example123;

-- Grant necessary permissions to example schema
GRANT CREATE SESSION TO example;
GRANT UNLIMITED TABLESPACE TO example;
GRANT CREATE TABLE TO example;

-- Create test user
CREATE USER t088503 IDENTIFIED BY hilaL250202;
GRANT CREATE SESSION TO t088503;

-- Create test table in example schema
CREATE TABLE example.test_data (
    id NUMBER GENERATED BY DEFAULT AS IDENTITY,
    name VARCHAR2(100),
    email VARCHAR2(100),
    age NUMBER,
    salary NUMBER(10,2),
    department VARCHAR2(50),
    hire_date DATE,
    status VARCHAR2(20),
    CONSTRAINT test_data_pk PRIMARY KEY (id)
);

-- Create a procedure to generate random data
CREATE OR REPLACE PROCEDURE example.generate_test_data AS
    v_name VARCHAR2(100);
    v_email VARCHAR2(100);
    v_age NUMBER;
    v_salary NUMBER(10,2);
    v_dept VARCHAR2(50);
    v_status VARCHAR2(20);
    v_departments VARCHAR2(200) := 'IT,HR,Finance,Marketing,Sales,Operations,Research';
    v_statuses VARCHAR2(100) := 'Active,Inactive,On Leave,Terminated';
BEGIN
    -- Generate 1,000,000 records
    FOR i IN 1..10000000 LOOP
        -- Generate random name
        v_name := DBMS_RANDOM.STRING('U', 1) || DBMS_RANDOM.STRING('L', 5) || ' ' ||
                  DBMS_RANDOM.STRING('U', 1) || DBMS_RANDOM.STRING('L', 7);
        
        -- Generate email based on name
        v_email := LOWER(REGEXP_REPLACE(v_name, '[^a-zA-Z]', '')) || '@example.com';
        
        -- Random age between 20 and 65
        v_age := TRUNC(DBMS_RANDOM.VALUE(20, 65));
        
        -- Random salary between 30000 and 150000
        v_salary := ROUND(DBMS_RANDOM.VALUE(30000, 150000), 2);
        
        -- Random department
        v_dept := REGEXP_SUBSTR(v_departments, '[^,]+', 1, 
                 TRUNC(DBMS_RANDOM.VALUE(1, REGEXP_COUNT(v_departments, ',') + 2)));
                 
        -- Random status
        v_status := REGEXP_SUBSTR(v_statuses, '[^,]+', 1,
                   TRUNC(DBMS_RANDOM.VALUE(1, REGEXP_COUNT(v_statuses, ',') + 2)));

        -- Insert the record
        INSERT INTO example.test_data (
            name, email, age, salary, department, hire_date, status
        ) VALUES (
            v_name,
            v_email,
            v_age,
            v_salary,
            v_dept,
            TRUNC(SYSDATE - DBMS_RANDOM.VALUE(0, 3650)), -- Random date in last 10 years
            v_status
        );
        
        -- Commit every 10000 records
        IF MOD(i, 10000) = 0 THEN
            COMMIT;
        END IF;
    END LOOP;
    
    -- Final commit
    COMMIT;
END;
/

-- Execute the procedure
EXEC example.generate_test_data;

-- Create indexes for better performance
CREATE INDEX example.test_data_dept_idx ON example.test_data(department);
CREATE INDEX example.test_data_status_idx ON example.test_data(status);
CREATE INDEX example.test_data_hire_date_idx ON example.test_data(hire_date);

-- Gather statistics for better query optimization
EXEC DBMS_STATS.GATHER_TABLE_STATS('EXAMPLE', 'TEST_DATA');

-- Grant select permission to the test user
GRANT SELECT ON example.test_data TO t088503; 