# DB Client API

A powerful and flexible Database Client API built with FastAPI that handles database queries asynchronously with user-specific queues and settings.

## Features

- **User Authentication**: Secure JWT-based authentication system
- **User Settings Management**:
  - Customizable export locations
  - Configurable export file types
  - Parallel processing limits per user
- **Asynchronous Query Processing**:
  - User-specific query queues
  - Parallel query execution with configurable limits
  - Real-time status updates

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **Python 3.8+**: Core programming language
- **JWT**: JSON Web Tokens for authentication
- **Pydantic**: Data validation using Python type annotations

## Project Structure

```
db-client-api/
├── app/
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── auth.py
│   │   │   ├── queries.py
│   │   │   └── users.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── schemas/
│   │   │   ├── query.py
│   │   │   └── user.py
│   │   └── services/
│   │       ├── query_executor.py
│   │       └── queue_manager.py
│   ├── tests/
│   ├── .env
│   ├── requirements.txt
│   └── main.py
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/db-client-api.git
cd db-client-api
```

2. Create a virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env` file:
```
SECRET_KEY=your_secret_key
DATABASE_URL=your_database_url
```

## API Endpoints

### Authentication
- `POST /auth/login`: User login
- `POST /auth/register`: User registration

### User Management
- `GET /users/me`: Get current user details
- `PUT /users/me/settings`: Update user settings

### Query Operations
- `POST /queries/`: Submit new query
- `GET /queries/{query_id}`: Get query status
- `GET /queries/`: List user's queries

## Request Example

```json
{
    "db_username": "user",
    "db_password": "password",
    "db_tns": "database_tns",
    "query": "SELECT * FROM table",
    "export_location": "/optional/path",  // Optional
    "export_type": "csv"                 // Optional
}
```

## Response Example

```json
{
    "query_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "queued",
    "position": 1,
    "submitted_at": "2024-03-20T12:00:00Z"
}
```

## User Settings

Users can configure:
- Default export location
- Preferred export file type (CSV, Excel, JSON, etc.)
- Maximum parallel query limit
- Queue priority settings

## Security

- JWT-based authentication
- Encrypted password storage
- Rate limiting
- Input validation and sanitization

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages:

```json
{
    "error": "error_code",
    "message": "Detailed error message",
    "details": {}
}
```

## Development

1. Start the development server:
```bash
uvicorn main:app --reload
```

2. Access the API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request 