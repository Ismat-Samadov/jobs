# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r scraper/requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variables
ENV DB_HOST=""
ENV DB_PORT=""
ENV DB_USER=""
ENV DB_PASSWORD=""
ENV DB_NAME=""
ENV EMAIL=""
ENV PASSWORD=""

# Set the default command to run the first scraper
CMD ["python", "scraper/parser.py"]
