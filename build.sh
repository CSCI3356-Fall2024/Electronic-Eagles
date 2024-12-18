#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Setting up environment variables..."
export DEFAULT_FILE_STORAGE="storages.backends.gcloud.GoogleCloudStorage"
export GS_BUCKET_NAME="electronic-eagles"
export GOOGLE_APPLICATION_CREDENTIALS="$GOOGLE_APPLICATION_CREDENTIALS"

# Navigate to the directory containing manage.py
cd delivery3

# Modify this line as needed for your package manager (pip, poetry, etc.)
pip install -r ../requirements.txt

# Convert static asset files
python manage.py collectstatic --no-input

# Apply any outstanding database migrations
python manage.py migrate