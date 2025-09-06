#!/bin/bash

# Wait for Redis to be ready
until nc -z -v -w30 redis 6379
do
  echo "Waiting for Redis connection..."
  sleep 1
done
echo "Redis is up and running!"

# Wait for Elasticsearch to be ready
until curl --silent --fail elasticsearch:9200/_cluster/health
do
  echo "Waiting for Elasticsearch connection..."
  sleep 1
done
echo "Elasticsearch is up and running!"

# Execute the passed command
exec "$@"
