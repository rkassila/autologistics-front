# Autologistics Frontend

Streamlit frontend application for the Autologistics document processing system.

## Environment Variables

The application requires the following environment variable:

- `API_BASE_URL`: The base URL of the backend API (default: `http://localhost:8080/api/v1`)

For local development, create a `.env` file:
```
API_BASE_URL=http://localhost:8080/api/v1
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
streamlit run streamlit_app/app.py
```

## Cloud Run Deployment

### Build and Deploy

1. Build the Docker image:
```bash
docker build -t gcr.io/YOUR_PROJECT_ID/autologistics-front .
```

2. Push to Google Container Registry:
```bash
docker push gcr.io/YOUR_PROJECT_ID/autologistics-front
```

3. Deploy to Cloud Run:
```bash
gcloud run deploy autologistics-front \
  --image gcr.io/YOUR_PROJECT_ID/autologistics-front \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars API_BASE_URL=https://YOUR_BACKEND_URL/api/v1 \
  --port 8080
```

Replace:
- `YOUR_PROJECT_ID` with your GCP project ID
- `YOUR_BACKEND_URL` with your backend Cloud Run service URL

### Environment Variable in Cloud Run

Make sure to set the `API_BASE_URL` environment variable in Cloud Run to point to your backend service. This can be done:
- During deployment using `--set-env-vars` flag
- Through the Cloud Console UI
- Using `gcloud run services update` command

Example:
```bash
gcloud run services update autologistics-front \
  --set-env-vars API_BASE_URL=https://your-backend-service-url.run.app/api/v1 \
  --region us-central1
```
