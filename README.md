# Business Logic Service

The Business Logic Service handles the core business functionality of the Slotify application, including appointment booking, service management, availability scheduling, and user profile management.

## Features

- **Appointment Management**: Create, view, update, and cancel appointments
- **Service Management**: CRUD operations for business services
- **Availability Scheduling**: Define and manage provider availability
- **Time Slot Calculation**: Smart calculation of available booking slots
- **Profile Management**: User profile viewing and updates
- **Role-Based Access Control**: Customer and staff role enforcement
- **JWT Authentication**: Token-based authentication via Flask-JWT-Extended
- **Prometheus Metrics**: Built-in monitoring and metrics exposure
- **Health Check Endpoint**: Kubernetes-ready health checks

## Tech Stack

- **Framework**: Flask 2.3.2
- **Authentication**: Flask-JWT-Extended
- **Password Hashing**: bcrypt
- **Monitoring**: Prometheus Flask Exporter
- **HTTP Client**: requests
- **Runtime**: Python 3.13

## Prerequisites

- Python 3.13+
- Authentication Service running (for JWT validation)
- Database Service running (for data persistence)

## Installation

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (optional):
```bash
export JWT_SECRET_KEY="your-secret-key"
export DB_SERVICE_URL="http://localhost:5003"
```

3. Run the service:
```bash
python app.py
```

The service will start on `http://localhost:5002`

### Docker

Build and run using Docker:

```bash
docker build -t business-service .
docker run -p 5002:5002 \
  -e JWT_SECRET_KEY="your-secret-key" \
  -e DB_SERVICE_URL="http://db-service:5003" \
  business-service
```

Or pull from Docker Hub:

```bash
docker pull alexnv67/logic-service
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JWT_SECRET_KEY` | Secret key for JWT token validation (must match Auth Service) | `super-secret-key` |
| `DB_SERVICE_URL` | URL of the Database Service | `http://db-service:5003` |

## API Endpoints

### Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "business-logic"
}
```

---

## Profile Endpoints

### Get My Profile
```http
GET /profile
Authorization: Bearer <jwt_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com",
  "role": "customer"
}
```

### Update My Profile
```http
PUT /profile
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "John Updated",
  "email": "new@example.com",
  "password": "newpassword"
}
```

---

## Service Endpoints

### Get All Services (Public)
```http
GET /services
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Haircut",
    "description": "Standard haircut",
    "duration": 30,
    "price": 25.00
  }
]
```

### Create Service (Staff Only)
```http
POST /services
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "Haircut",
  "description": "Standard haircut",
  "duration": 30,
  "price": 25.00
}
```

### Update Service (Staff Only)
```http
PUT /services/<service_id>
Authorization: Bearer <jwt_token>
```

### Delete Service (Staff Only)
```http
DELETE /services/<service_id>
Authorization: Bearer <jwt_token>
```

---

## Appointment Endpoints

### Get My Appointments (Customer)
```http
GET /appointments/me
Authorization: Bearer <jwt_token>
```

### Create Appointment (Customer)
```http
POST /appointments
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "service_id": 1,
  "date": "2026-01-15",
  "time": "10:00"
}
```

**Response:** `201 Created`

### Update My Appointment (Customer)
```http
PUT /appointments/me/<appointment_id>
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "date": "2026-01-16",
  "time": "11:00"
}
```

### Delete My Appointment (Customer)
```http
DELETE /appointments/me/<appointment_id>
Authorization: Bearer <jwt_token>
```

### Get All Appointments (Staff)
```http
GET /appointments
Authorization: Bearer <jwt_token>
```

### Get Appointments by Date (Staff)
```http
GET /appointments/date/<date>
Authorization: Bearer <jwt_token>
```

### Update Appointment (Staff)
```http
PUT /appointments/<appointment_id>
Authorization: Bearer <jwt_token>
```

### Delete Appointment (Staff)
```http
DELETE /appointments/<appointment_id>
Authorization: Bearer <jwt_token>
```

---

## Availability Endpoints

### Get Availability by Date (Staff)
```http
GET /availability/<date>
Authorization: Bearer <jwt_token>
```

### Define Availability (Staff)
```http
POST /availability
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "date": "2026-01-15",
  "start_time": "09:00",
  "end_time": "17:00"
}
```

**Note:** Overlapping time slots are not allowed.

### Delete Availability (Staff)
```http
DELETE /availability/<availability_id>
Authorization: Bearer <jwt_token>
```

**Note:** Cannot delete if appointments are booked during that time.

### Get Available Time Slots (Customer)
```http
GET /available-timeslots?date=2026-01-15&service_id=1
Authorization: Bearer <jwt_token>
```

**Response:** `200 OK`
```json
{
  "available_slots": [
    "09:00",
    "09:10",
    "09:20",
    "10:00"
  ]
}
```

---

## Role-Based Access Control

The service enforces role-based access control using JWT claims:

- **Customer Role**: Can manage their own appointments and profile
- **Staff Role**: Can manage all appointments, services, and availability
- **Any Authenticated User**: Can view and update their profile

Roles are validated using the `@requires_role()` decorator in `utils.py`.

## Business Logic

### Time Slot Validation

The service includes sophisticated time slot validation:

1. **Overlap Prevention**: Prevents double-booking by checking existing appointments
2. **Availability Matching**: Ensures appointments fall within defined availability windows
3. **Duration Awareness**: Considers service duration when calculating available slots
4. **10-Minute Intervals**: Generates time slots in 10-minute increments

### Availability Management

- Staff can define multiple availability windows per day
- Overlapping availability slots are rejected
- Availability cannot be deleted if appointments are already booked

## Architecture

The Business Logic Service is part of a microservices architecture:

```
Client -> Business Service (Port 5002) -> Database Service (Port 5003) -> PostgreSQL
                  |
                  v
          Auth Service (Port 5001) - JWT validation
```

- **Stateless**: Does not maintain session state
- **JWT-based**: Validates tokens issued by Auth Service
- **Microservice**: Communicates with DB Service via HTTP

## Project Structure

```
business-service/
├── app.py                  # Main Flask application
├── utils.py                # Helper functions and decorators
├── requirements.txt        # Python dependencies
├── Dockerfile             # Container image definition
├── routes/
│   ├── __init__.py        # Blueprint registration
│   ├── profile.py         # User profile endpoints
│   ├── services.py        # Service CRUD endpoints
│   ├── appointments.py    # Appointment management
│   └── availability.py    # Availability management
└── .github/
    └── workflows/
        └── docker-publish.yml  # CI/CD pipeline
```

## Metrics

Prometheus metrics are automatically exposed at:
```
GET /metrics
```

Includes standard HTTP metrics for all endpoints.

## CI/CD

The service uses GitHub Actions for continuous deployment:

- **Trigger**: Push to `main` branch
- **Action**: Builds Docker image and pushes to Docker Hub
- **Image**: `alexnv67/logic-service`
- **Workflow**: `.github/workflows/docker-publish.yml`

## Development Notes

- Debug mode is disabled in production (`debug=False`)
- All endpoints (except health check and GET /services) require authentication
- JWT secret must match the one used by Authentication Service
- Service duration is measured in minutes
- Time slots are generated in 10-minute intervals
- Dates should be in `YYYY-MM-DD` format
- Times should be in `HH:MM` format (24-hour)

## Security Considerations

⚠️ **Important:**
- Ensure `JWT_SECRET_KEY` matches across all services
- Validate input data to prevent injection attacks
- Implement rate limiting to prevent abuse
- Add HTTPS in production
- Consider adding request validation middleware
- Implement comprehensive logging for audit trails

## Error Handling

The service returns appropriate HTTP status codes:

- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid input or business logic violation
- `401 Unauthorized` - Missing or invalid JWT token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found

## Testing Considerations

When testing:
- Use valid JWT tokens from the Authentication Service
- Ensure Database Service is accessible
- Test role-based access control thoroughly
- Validate time slot calculation logic
- Test overlap prevention mechanisms

## Related Services

- **Authentication Service**: Issues JWT tokens
- **Database Service**: Handles data persistence

## License

Part of the Slotify platform.
