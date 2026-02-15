# Use the official SearXNG image (2026 stable release)
FROM searxng/searxng:latest

# Set environment variables for better defaults
ENV BASE_URL=http://localhost:8080/
ENV INSTANCE_NAME=my-private-search

# Copy your local settings into the container's config path
# The official container expects config at /etc/searxng/
COPY ./settings.yml /etc/searxng/settings.yml

# Expose the default SearXNG port
EXPOSE 8080

# Health check to ensure the service is running correctly
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:8080/status || exit 1
