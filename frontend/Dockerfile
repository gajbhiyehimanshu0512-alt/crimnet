# Multi-stage build for React frontend
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files for dependency caching
COPY package*.json ./

# Install dependencies (layer is cached until package*.json changes)
RUN npm ci

# Copy source code
COPY . .

# Build production bundle
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:1.27-alpine

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built application from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx:alpine already provides a non-root nginx user

EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
