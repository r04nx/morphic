# Morphic Database Credentials

## PostgreSQL Database
- **Host**: localhost
- **Port**: 5432
- **Database**: morphic
- **Username**: morphic_user
- **Password**: morphic_password_2024
- **Connection URL**: `postgresql://morphic_user:morphic_password_2024@localhost:5432/morphic`

## Neo4j Database
- **URI**: bolt://localhost:7687
- **HTTP Interface**: http://localhost:7474
- **Username**: neo4j
- **Password**: morphic_neo4j_password_2024
- **Default Database**: morphic
- **Connection URL**: `bolt://neo4j:morphic_neo4j_password_2024@localhost:7687`

## Redis Cache
- **Host**: localhost
- **Port**: 6379
- **Password**: morphic_redis_password_2024
- **Connection URL**: `redis://:morphic_redis_password_2024@localhost:6379`

## Environment Variables
Add these to your backend `.env` file:

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=morphic
POSTGRES_USER=morphic_user
POSTGRES_PASSWORD=morphic_password_2024
DATABASE_URL=postgresql://morphic_user:morphic_password_2024@localhost:5432/morphic

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=morphic_neo4j_password_2024
NEO4J_DATABASE=morphic

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=morphic_redis_password_2024
REDIS_URL=redis://:morphic_redis_password_2024@localhost:6379
```

## Docker Management Commands

### Start all services:
```bash
docker-compose up -d
```

### Stop all services:
```bash
docker-compose down
```

### View logs:
```bash
docker-compose logs -f postgres
docker-compose logs -f neo4j
docker-compose logs -f redis
```

### Access databases directly:

#### PostgreSQL:
```bash
docker exec -it morphic-postgres psql -U morphic_user -d morphic
```

#### Neo4j Browser:
Visit http://localhost:7474 in your browser
- Username: neo4j
- Password: morphic_neo4j_password_2024

#### Redis CLI:
```bash
docker exec -it morphic-redis redis-cli -a morphic_redis_password_2024
```

## Database Schema
The PostgreSQL database has been initialized with:
- `incidents` table - stores incident records
- `incident_logs` table - stores log timeline for each incident
- `remediation_actions` table - stores automated actions taken

Neo4j is ready for graph-based relationships between incidents, services, and dependencies.

## Security Notes
- These credentials are for development use only
- In production, use stronger passwords and consider using secrets management
- All databases are exposed on localhost only
- Consider using Docker secrets or environment variable files for production
