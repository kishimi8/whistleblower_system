# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /code

# Install system dependencies
RUN apt-get update \
    && apt-get install -y build-essential libpq-dev curl poppler-utils libmagic1 \
    && apt-get clean

# Install Node.js and npm
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install npm dependencies
COPY package.json package-lock.json* /code/

# Copy the Django project code into the container
COPY . /code/

# Install Tailwind CSS
RUN npm install -D tailwindcss

# Build Tailwind CSS
RUN npx tailwindcss -i ./static/src/input.css -o ./static/src/output.css

RUN mkdir -p /code/staticfiles && chmod -R 755 /code/staticfiles

RUN python manage.py collectstatic --noinput

# Expose the port Gunicorn will run on
EXPOSE 8059

# Run with gunicorn
CMD ["sh", "-c", "PYTHONPATH=/code gunicorn --bind 0.0.0.0:8059 --workers 3 --access-logfile - --error-logfile - --log-level info WhistleBlower.asgi:application -k uvicorn.workers.UvicornWorker --timeout 300"]

#CMD ["sh", "-c", "PYTHONPATH=/code gunicorn WhistleBlower.wsgi:application --bind 0.0.0.0:8059"]


