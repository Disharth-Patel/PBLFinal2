# Validated Runtime Configuration

Production settings should reject default JWT secrets, wildcard or localhost CORS, invalid URLs, and unsafe rate-limit/token values at startup.

## What Happened
The hardening pass centralized these checks in the Pydantic settings model and made Docker Compose require deployment-provided secrets and origins.

## Takeaway
Keep environment validation in configuration construction so invalid production deployments fail before the application serves traffic.

## History
- 2026-11-07 (PBLFinal2/production-hardening): initial
