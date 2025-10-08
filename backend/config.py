# Configuration for SMART on FHIR Backend
import os

# Client configuration
CLIENT_ID = os.getenv("CLIENT_ID", "your-client-id-here")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "")

# Server configuration
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "9001"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3002")

# OAuth2 configuration
REDIRECT_URI = f"http://localhost:{BACKEND_PORT}/callback"
SCOPE = "launch/patient patient/*.read patient/Patient.read patient/Observation.read patient/Encounter.read"

# FHIR resource configuration
FHIR_RESOURCES = {
    "patient": "Patient",
    "observations": "Observation?category=vital-signs",
    "encounters": "Encounter"
}
