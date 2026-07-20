# Docker Setup for DMS

This document provides instructions for setting up and running the DMS project using Docker and Docker Compose.

## Prerequisites

- Docker
- Docker Compose

## Getting Started

1.  **Create a `.env` file:**
    Copy the example environment file to create your own local configuration:
    ```bash
    cp backend/.env.example backend/.env
    ```

2.  **Review and update `.env`:**
    Open `backend/.env` and update the variables as needed. At a minimum, you should ensure that `POSTGRES_PASSWORD` and `REDIS_PASSWORD` are set.

3.  **Build and start the services:**
    Use Docker Compose to build the images and start the containers:
    ```bash
    docker-compose up --build
    ```
    This will start the `postgres`, `redis`, `backend`, and `frontend` services.

4.  **Access the application:**
    -   **Frontend:** [http://localhost:3000](http://localhost:3000)
    -   **Backend API:** [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

## Services

The `docker-compose.yml` file defines the following services:

-   `postgres`: The PostgreSQL database for the application.
-   `redis`: The Redis instance for caching and background jobs.
-   `backend`: The Python backend application.
-   `frontend`: The Next.js frontend application.

## Troubleshooting

-   If you encounter issues with the backend starting, ensure that the `postgres` and `redis` services are healthy before the backend starts. The `depends_on` configuration in `docker-compose.yml` should handle this.
-   Make sure the ports `5432`, `6379`, `8000`, and `3000` are not in use by other applications.
