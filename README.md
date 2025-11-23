# Autologistics Frontend

Streamlit frontend application for the Autologistics document processing system. Provides a user-friendly interface for uploading PDFs, reviewing extracted data, and monitoring model performance.

**Backend Repository:** [autologistics](https://github.com/rkassila/autologistics)

## Features

- PDF document upload and extraction
- Interactive form for reviewing and correcting extracted fields
- Real-time modification detection
- Document database viewing and management
- Model log viewing with performance analytics
- Interactive graphs showing success rates and corrections over time
- Automatic model log creation when saving documents

## Project Structure

```
autologistics-front/
├── streamlit_app/
│   ├── app.py                    # Main document upload and review UI
│   └── pages/
│       ├── database_check.py     # View and manage logistics documents
│       └── database_check_model.py  # View model logs with analytics
├── Dockerfile                    # Docker configuration
├── requirements.txt              # Python dependencies
└── README.md
```

## Environment Variables

The application requires the following environment variable:

- `API_BASE_URL`: The base URL of the backend API (default: `http://localhost:8080/api/v1`)

For local development, create a `.env` file:
```env
API_BASE_URL=http://localhost:8080/api/v1
```

## Local Development

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Environment Variable

Create a `.env` file or export the variable:
```bash
export API_BASE_URL=http://localhost:8080/api/v1
```

### 3. Run the Application

```bash
streamlit run streamlit_app/app.py
```

The application will be available at `http://localhost:8501`

## Pages

### Main Page (`app.py`)
- Upload PDF documents
- Extract and review structured fields
- Edit extracted values before saving
- Save documents (automatically creates model log entries)
- View modification summary

### Database Check (`pages/database_check.py`)
- View all saved logistics documents
- Search and filter documents
- View document details
- Delete documents

### Model Log Analytics (`pages/database_check_model.py`)
- View all model log entries
- Performance graphs:
  - Overall success vs corrections bar chart
  - Success distribution pie chart
  - Time series showing success/correction rates per minute
- Detailed log entry information
- Table view of all logs

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

### Update Environment Variable

If you need to update the API URL after deployment:

```bash
gcloud run services update autologistics-front \
  --set-env-vars API_BASE_URL=https://your-backend-service-url.run.app/api/v1 \
  --region us-central1
```

Or use the Cloud Console:
1. Go to Cloud Run → Your service
2. Click **"Edit & Deploy New Revision"**
3. Go to **"Variables & Secrets"** tab
4. Update `API_BASE_URL`
5. Click **"Deploy"**

## Workflow

1. **Upload PDF**: User uploads a logistics document PDF
2. **Extract**: Backend extracts text and structured fields using OpenAI
3. **Review**: User reviews extracted fields in an editable form
4. **Modify** (optional): User can correct any extracted values
5. **Save**: User clicks "Save" button which:
   - Saves document to `logistics_documents` table
   - Automatically creates model log entry in `model_log` table
   - Tracks original vs corrected values
   - Records success status based on whether corrections were made

## Dependencies

- `streamlit` - Web framework
- `requests` - HTTP client for API calls
- `pandas` - Data manipulation
- `plotly` - Interactive graphs
- `python-dotenv` - Environment variable management

## Troubleshooting

### Connection Issues
- Verify `API_BASE_URL` points to the correct backend URL
- Check that the backend service is running and accessible
- Ensure CORS is enabled in the backend (already configured)

### Graph Display Issues
- Ensure `plotly` is installed: `pip install plotly`
- Check browser console for JavaScript errors
- Verify model log data exists in the database

### Form Submission Issues
- Check that all required fields are filled
- Verify backend API is responding correctly
- Check browser network tab for API errors
