# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Redis Cluster support
  - New RedisAdapter class for unified Redis operations
  - Transparent switching between single-node and cluster modes
  - Retry mechanism with exponential backoff for Redis operations
  - Environment-based configuration for deployment flexibility
- Development workflow improvements: Hot reloading setup for all services (webapp, scheduler, controller) with volume mounts and optimized Docker builds
- Enhanced Docker Compose configuration
  - Support for both single Redis instance and Redis Cluster deployments
  - Development profile with single Redis node
  - Production profile with 3 master + 3 replica Redis Cluster

### Changed

- Refactored services to use dependency injection for Redis clients
- Updated installation documentation with Redis Cluster setup instructions
- Improved error handling and connection management in Redis operations

## [0.0.1] - 2025-06-15

### Added

- Core elevator simulation system architecture
  - Elevator model with state management
  - Request handling (internal/external)
  - Movement and door control simulation
- Redis-based communication infrastructure
  - Pub/Sub channels for real-time commands and status
  - Streams for reliable request queueing
  - State persistence using Redis key-value storage
- Microservices architecture
  - FastAPI web application for HTTP endpoints
  - Scheduler service for elevator request assignment
  - Controller service for elevator movement simulation
  - Each service containerized with Docker
- Web Dashboard
  - Real-time elevator status display using HTMX
  - External request monitoring
  - Minimal JavaScript requirements
- API Endpoints
  - External elevator requests (floor calls)
  - Internal elevator requests (destination buttons)
  - Elevator status queries
  - Request stream management
- Development Infrastructure
  - Docker Compose setup
  - Development environment configuration
  - API testing with Bruno collections
- Documentation
  - Architecture overview diagram
  - Installation guide
  - README with system design details

### Technical Details

- Python 3.12 base implementation
- Redis 7.2 for messaging and state management
- FastAPI for web services
- HTMX for dynamic UI updates
- Structured logging with `structlog`
- Type hints throughout codebase
- Async/await patterns for concurrent operations

[Unreleased]: https://github.com/hoangquochung1110/redis-pubsub-101/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/hoangquochung1110/redis-pubsub-101/releases/tag/v0.0.1
