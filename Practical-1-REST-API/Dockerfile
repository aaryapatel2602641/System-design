# Start from a small official Python image
FROM python:3.12-slim

# All work happens inside /app in the container
WORKDIR /app

# Copy just the requirements first so Docker can cache the pip install layer
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code into the image
COPY . .

# The app listens on 5001 (matches app.run(port=5001) in rest_api.py)
EXPOSE 5001

# Command that runs when the container starts
CMD ["python", "rest_api.py"]