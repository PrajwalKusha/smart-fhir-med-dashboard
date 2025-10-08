from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import json
import secrets
import base64
import hashlib
import uuid
import time
import requests
import urllib.parse
from urllib.parse import urlencode, parse_qs
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SMART on FHIR Backend", version="1.0.0")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3002"],  # React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory session store (for prototype only)
# In production, replace with proper database storage
SESSIONS = {}  # session_id -> dict with tokens, endpoints, patient/practitioner ids

def decode_jwt_payload(jwt_token):
    """
    Decode JWT payload without verification (for prototype only)
    In production, you should verify the JWT signature using the server's public key
    """
    try:
        import base64
        import json
        
        # Split JWT into parts
        jwt_parts = jwt_token.split('.')
        if len(jwt_parts) < 2:
            raise ValueError("Invalid JWT format")
        
        # Decode the payload (second part)
        payload_encoded = jwt_parts[1]
        # Add padding if needed
        payload_encoded += '=' * (4 - len(payload_encoded) % 4)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded)
        payload = json.loads(payload_decoded)
        
        return payload
        
    except Exception as e:
        logger.warning(f"Failed to decode JWT: {e}")
        return None

@app.get("/")
async def root():
    return {"message": "SMART on FHIR Backend is running"}

@app.get("/test-smart-config/{iss}")
async def test_smart_config(iss: str):
    """
    Test endpoint to verify SMART configuration discovery
    """
    try:
        smart_config_url = f"{iss}/.well-known/smart-configuration"
        logger.info(f"Testing SMART configuration discovery: {smart_config_url}")
        
        config_response = requests.get(smart_config_url, timeout=10)
        config_response.raise_for_status()
        smart_config = config_response.json()
        
        return {
            "status": "success",
            "smart_config_url": smart_config_url,
            "authorization_endpoint": smart_config.get("authorization_endpoint"),
            "token_endpoint": smart_config.get("token_endpoint"),
            "issuer": smart_config.get("issuer"),
            "jwks_uri": smart_config.get("jwks_uri"),
            "response_types_supported": smart_config.get("response_types_supported"),
            "scopes_supported": smart_config.get("scopes_supported")
        }
        
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": str(e),
            "smart_config_url": smart_config_url
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.get("/launch")
async def launch_app(request: Request):
    """
    SMART on FHIR launch endpoint
    Receives launch and iss parameters from SMART App Launcher
    Follows SMART on FHIR best practices for launch flow
    """
    # Extract launch parameters
    launch = request.query_params.get("launch")
    iss = request.query_params.get("iss")
    
    logger.info(f"Received launch parameters:")
    logger.info(f"  launch: {launch}")
    logger.info(f"  iss: {iss}")
    
    if not launch or not iss:
        raise HTTPException(status_code=400, detail="Missing required parameters: launch and iss")
    
    try:
        # 1) Discover SMART configuration from .well-known/smart-configuration
        logger.info(f"Discovering SMART configuration from {iss}/.well-known/smart-configuration")
        smart_config_url = f"{iss}/.well-known/smart-configuration"
        
        # Use requests for synchronous call to SMART configuration
        config_response = requests.get(smart_config_url, timeout=10)
        config_response.raise_for_status()
        smart_config = config_response.json()
        
        auth_url = smart_config["authorization_endpoint"]
        token_url = smart_config["token_endpoint"]
        
        logger.info(f"Discovered endpoints:")
        logger.info(f"  authorization_endpoint: {auth_url}")
        logger.info(f"  token_endpoint: {token_url}")
        
        # 2) Create session with UUID
        session_id = str(uuid.uuid4())
        current_time = time.time()
        
        SESSIONS[session_id] = {
            # FHIR server information
            "fhir_base": iss,
            "auth_endpoint": auth_url,
            "token_endpoint": token_url,
            
            # Launch context
            "launch": launch,
            "client_id": "my_web_app",  # SMART Health IT Sandbox client ID
            "redirect_uri": "http://localhost:9001/callback",
            "scope": "openid fhirUser patient/*.read",
            
            # OAuth2 tokens (to be populated)
            "access_token": None,
            "refresh_token": None,
            "expires_at": None,
            
            # Patient/Practitioner context (to be populated from launch context)
            "patient_id": None,
            "practitioner_id": None,
            
            # Session metadata
            "created_at": current_time,
            "last_accessed": current_time,
            "status": "launched"
        }
        
        # 3) Build authorize URL with state = session_id
        auth_params = {
            "response_type": "code",
            "client_id": "my_web_app",  # SMART Health IT Sandbox client ID
            "redirect_uri": "http://localhost:9001/callback",
            "scope": "openid fhirUser patient/*.read",
            "launch": launch,
            "state": session_id,
            "aud": iss  # Required for SMART on FHIR - audience parameter
        }
        
        redirect_url = auth_url + "?" + urllib.parse.urlencode(auth_params)
        logger.info(f"Redirecting to authorization URL: {redirect_url}")
        
        return RedirectResponse(url=redirect_url)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error discovering SMART configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to discover SMART configuration: {str(e)}")
    except KeyError as e:
        logger.error(f"Missing required field in SMART configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Invalid SMART configuration: missing {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during launch: {e}")
        raise HTTPException(status_code=500, detail=f"Launch failed: {str(e)}")

@app.get("/callback")
async def oauth_callback(code: str = None, state: str = None, error: str = None):
    """
    OAuth2 callback endpoint
    Handles the authorization code and exchanges it for an access token
    Uses session_id as state parameter for CSRF protection
    """
    logger.info(f"OAuth callback received:")
    logger.info(f"  code: {code}")
    logger.info(f"  state: {state}")
    logger.info(f"  error: {error}")
    
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state parameter")
    
    # Validate state matches a session
    session = SESSIONS.get(state)
    if not session:
        raise HTTPException(status_code=400, detail="Invalid session/state")
    
    try:
        # POST to token_endpoint to exchange code for tokens
        logger.info(f"Exchanging authorization code for access token at {session['token_endpoint']}")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": session["redirect_uri"],
            "client_id": session["client_id"],
            "aud": session["fhir_base"]  # Required for SMART on FHIR - audience parameter
            # Include client_secret if your client is confidential
            # "client_secret": session.get("client_secret")
        }
        
        # Use requests for synchronous token exchange (server-side only)
        token_resp = requests.post(session["token_endpoint"], data=token_data, timeout=30)
        token_resp.raise_for_status()
        token_response = token_resp.json()
        
        if "access_token" not in token_response:
            logger.error(f"Token exchange failed: {token_response}")
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Store tokens in session
        session["access_token"] = token_response.get("access_token")
        session["refresh_token"] = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)
        session["expires_at"] = time.time() + int(expires_in)
        
        # Update session status and metadata
        session["status"] = "authenticated"
        session["last_accessed"] = time.time()
        
        # Extract patient/practitioner context from multiple sources
        patient_id = None
        practitioner_id = None
        encounter_id = None
        
        # 1) Check token_response for direct patient/practitioner attributes (common in SMART)
        if "patient" in token_response:
            patient_id = token_response["patient"]
            logger.info(f"Patient context found in token response: {patient_id}")
        
        if "practitioner" in token_response:
            practitioner_id = token_response["practitioner"]
            logger.info(f"Practitioner context found in token response: {practitioner_id}")
        
        if "encounter" in token_response:
            encounter_id = token_response["encounter"]
            logger.info(f"Encounter context found in token response: {encounter_id}")
        
        # 2) Parse id_token (JWT) for patient claim if present
        if "id_token" in token_response:
            id_token = token_response["id_token"]
            logger.info("ID token received, attempting to decode for patient context")
            
            # Decode JWT payload
            payload = decode_jwt_payload(id_token)
            if payload:
                logger.info(f"ID token payload decoded successfully")
                
                # Extract patient/practitioner from JWT claims
                if "patient" in payload and not patient_id:
                    patient_id = payload["patient"]
                    logger.info(f"Patient context found in ID token: {patient_id}")
                
                if "practitioner" in payload and not practitioner_id:
                    practitioner_id = payload["practitioner"]
                    logger.info(f"Practitioner context found in ID token: {practitioner_id}")
                
                if "encounter" in payload and not encounter_id:
                    encounter_id = payload["encounter"]
                    logger.info(f"Encounter context found in ID token: {encounter_id}")
                
                # Log other useful claims
                if "sub" in payload:
                    logger.info(f"Subject (user) from ID token: {payload['sub']}")
                if "aud" in payload:
                    logger.info(f"Audience from ID token: {payload['aud']}")
                if "iss" in payload:
                    logger.info(f"Issuer from ID token: {payload['iss']}")
                if "exp" in payload:
                    logger.info(f"Token expiration from ID token: {payload['exp']}")
                if "iat" in payload:
                    logger.info(f"Token issued at from ID token: {payload['iat']}")
            else:
                logger.warning("Failed to decode ID token payload")
        
        # 3) Check if patient context was provided in launch parameter
        # Some SMART servers pass patient context via launch parameter
        launch_context = session.get("launch")
        if launch_context and not patient_id:
            logger.info(f"Launch context available: {launch_context}")
            # In some implementations, you might need to make an additional call
            # to resolve the launch context to get patient information
            # For now, we'll log it for debugging
            logger.info("Launch context present but patient resolution not implemented")
        
        # 4) Store discovered context in session
        if patient_id:
            session["patient_id"] = patient_id
        if practitioner_id:
            session["practitioner_id"] = practitioner_id
        if encounter_id:
            session["encounter_id"] = encounter_id
        
        # 5) Log final context discovery results
        logger.info("=== Context Discovery Results ===")
        logger.info(f"Patient ID: {session.get('patient_id', 'Not found')}")
        logger.info(f"Practitioner ID: {session.get('practitioner_id', 'Not found')}")
        logger.info(f"Encounter ID: {session.get('encounter_id', 'Not found')}")
        
        # 6) If no patient context found, log warning
        if not session.get("patient_id"):
            logger.warning("No patient context discovered - user may need to select patient")
            logger.info("This is normal for some SMART implementations where patient selection happens in the launcher")
        
        logger.info("Successfully obtained access token")
        logger.info(f"Session updated: patient_id={session.get('patient_id')}, practitioner_id={session.get('practitioner_id')}")
        
        # Redirect to frontend with success (state is session_id)
        return RedirectResponse(url="http://localhost:3002?token=" + state)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Token exchange request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error during token exchange: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to exchange code for token: {str(e)}")

@app.get("/ui")
async def session_ui(session_id: str = None):
    """
    Session status UI endpoint
    Shows session information and provides links to patient data
    """
    if not session_id:
        return {"error": "session_id parameter required"}
    
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found"}
    
    # Check if session is authenticated
    if session.get("status") != "authenticated":
        return {
            "error": "Session not authenticated",
            "status": session.get("status"),
            "session_id": session_id
        }
    
    # Check if access token is still valid
    current_time = time.time()
    expires_at = session.get("expires_at", 0)
    
    if current_time >= expires_at:
        return {
            "error": "Access token expired",
            "expires_at": expires_at,
            "current_time": current_time,
            "session_id": session_id
        }
    
    return {
        "status": "success",
        "session_id": session_id,
        "authenticated": True,
        "patient_id": session.get("patient_id"),
        "practitioner_id": session.get("practitioner_id"),
        "encounter_id": session.get("encounter_id"),
        "fhir_base": session.get("fhir_base"),
        "expires_at": expires_at,
        "time_remaining": expires_at - current_time,
        "links": {
            "patient_data": f"/patient-data/{session_id}",
            "session_info": f"/session/{session_id}",
            "frontend": f"http://localhost:3002?token={session_id}"
        }
    }

def ensure_token_valid(session):
    """
    Ensure the access token is valid, refresh if needed
    """
    if session.get("expires_at", 0) > time.time() + 30:
        return  # still valid
    
    # expired or about to
    if session.get("refresh_token"):
        logger.info("Access token expired or expiring soon, attempting refresh")
        
        try:
            resp = requests.post(session["token_endpoint"], data={
                "grant_type": "refresh_token",
                "refresh_token": session["refresh_token"],
                "client_id": session["client_id"]
                # client_secret if required
                # "client_secret": session.get("client_secret")
            }, timeout=30).json()
            
            if "access_token" in resp:
                session["access_token"] = resp["access_token"]
                session["refresh_token"] = resp.get("refresh_token", session["refresh_token"])
                session["expires_at"] = time.time() + int(resp.get("expires_in", 3600))
                session["last_accessed"] = time.time()
                logger.info("Token refresh successful")
                return
            else:
                logger.error(f"Token refresh failed: {resp}")
                raise Exception("Token refresh failed - no access_token in response")
                
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            # If refresh failed, mark session invalid and require re-launch
            session["needs_reauth"] = True
            raise Exception("Re-auth required")
    
    # If no refresh token, mark session invalid and require re-launch
    session["needs_reauth"] = True
    raise Exception("Re-auth required")

def fetch_fhir_resource(base_url, resource_path, headers, session, timeout=30):
    """
    Fetch a single FHIR resource with error handling and token refresh
    Returns (success, data, error_message, needs_reauth)
    """
    try:
        url = f"{base_url}/{resource_path}"
        logger.info(f"Fetching FHIR resource: {url}")
        
        response = requests.get(url, headers=headers, timeout=timeout)
        
        if response.status_code == 200:
            return True, response.json(), None, False
        elif response.status_code == 401:
            # Token expired or invalid, try to refresh
            logger.warning(f"Received 401 for {url}, attempting token refresh")
            try:
                ensure_token_valid(session)
                # Update headers with new token
                headers["Authorization"] = f"Bearer {session['access_token']}"
                # Retry the request
                retry_response = requests.get(url, headers=headers, timeout=timeout)
                if retry_response.status_code == 200:
                    logger.info(f"Request successful after token refresh: {url}")
                    return True, retry_response.json(), None, False
                else:
                    error_msg = f"HTTP {retry_response.status_code} after token refresh: {retry_response.text}"
                    return False, None, error_msg, False
            except Exception as refresh_error:
                logger.error(f"Token refresh failed for {url}: {refresh_error}")
                return False, None, f"Token refresh failed: {str(refresh_error)}", True
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, None, error_msg, False
            
    except requests.exceptions.Timeout:
        return False, None, "Request timeout", False
    except requests.exceptions.ConnectionError:
        return False, None, "Connection error", False
    except Exception as e:
        return False, None, f"Request failed: {str(e)}", False

@app.get("/patient-data/{session_id}")
async def get_patient_data(session_id: str):
    """
    Fetch patient data using the stored access token
    Returns Patient, Observation, and Encounter resources as JSON
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    
    # Ensure token is valid (refresh if needed)
    try:
        session = ensure_token_valid(session)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
    
    access_token = session.get("access_token")
    fhir_base = session.get("fhir_base")
    patient_id = session.get("patient_id")
    
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token available")
    
    # Prepare headers for FHIR requests
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/fhir+json",
        "User-Agent": "SMART-on-FHIR-Prototype/1.0"
    }
    
    # Initialize patient data structure with comprehensive metadata
    patient_data = {
        "patient": None,
        "observations": None,
        "encounters": None,
        "medications": None,
        "diagnostic_reports": None,
        "procedures": None,
        "metadata": {
            "fhir_server": fhir_base,
            "session_id": session_id,
            "patient_id": patient_id,
            "practitioner_id": session.get("practitioner_id"),
            "encounter_id": session.get("encounter_id"),
            "fetch_timestamp": time.time(),
            "resources_fetched": [],
            "resources_failed": [],
            "errors": [],
            "token_info": {
                "expires_at": session.get("expires_at"),
                "time_remaining": session.get("expires_at", 0) - time.time()
            }
        }
    }
    
    # Define resources to fetch with their queries
    resources_to_fetch = [
        {
            "name": "patient",
            "path": f"Patient/{patient_id}" if patient_id else "Patient",
            "description": "Patient information"
        },
        {
            "name": "observations",
            "path": f"Observation?patient={patient_id}&category=vital-signs&_sort=-date&_count=20" if patient_id else "Observation?category=vital-signs&_sort=-date&_count=20",
            "description": "Vital signs and observations"
        },
        {
            "name": "encounters",
            "path": f"Encounter?patient={patient_id}&_sort=-date&_count=10" if patient_id else "Encounter?_sort=-date&_count=10",
            "description": "Healthcare encounters"
        },
        {
            "name": "medications",
            "path": f"MedicationRequest?patient={patient_id}&_sort=-date&_count=5" if patient_id else "MedicationRequest?_sort=-date&_count=5",
            "description": "Current medications"
        },
        {
            "name": "diagnostic_reports",
            "path": f"DiagnosticReport?patient={patient_id}&_sort=-date&_count=5" if patient_id else "DiagnosticReport?_sort=-date&_count=5",
            "description": "Lab results and diagnostic reports"
        },
        {
            "name": "procedures",
            "path": f"Procedure?patient={patient_id}&_sort=-date&_count=5" if patient_id else "Procedure?_sort=-date&_count=5",
            "description": "Medical procedures"
        }
    ]
    
    # Fetch each resource with individual error handling
    for resource in resources_to_fetch:
        resource_name = resource["name"]
        resource_path = resource["path"]
        resource_description = resource["description"]
        
        logger.info(f"Fetching {resource_description} from {fhir_base}/{resource_path}")
        
        success, data, error_msg, needs_reauth = fetch_fhir_resource(fhir_base, resource_path, headers, session)
        
        if success:
            patient_data[resource_name] = data
            patient_data["metadata"]["resources_fetched"].append(resource_name)
            
            # Log resource-specific success info
            if data and "entry" in data:
                entry_count = len(data["entry"])
                logger.info(f"Successfully fetched {resource_description}: {entry_count} entries")
            else:
                logger.info(f"Successfully fetched {resource_description}: no entries")
        else:
            patient_data["metadata"]["resources_failed"].append(resource_name)
            patient_data["metadata"]["errors"].append(f"{resource_description}: {error_msg}")
            logger.warning(f"Failed to fetch {resource_description}: {error_msg}")
            
            # If re-authentication is needed, set flag and return early
            if needs_reauth:
                patient_data["metadata"]["needs_reauth"] = True
                patient_data["metadata"]["reauth_message"] = "Session expired - re-authentication required"
                logger.warning("Session requires re-authentication")
                break
    
    # Update session last accessed time
    session["last_accessed"] = time.time()
    
    # Log final summary
    logger.info("=== FHIR Resource Fetch Summary ===")
    logger.info(f"Resources fetched successfully: {patient_data['metadata']['resources_fetched']}")
    logger.info(f"Resources failed: {patient_data['metadata']['resources_failed']}")
    if patient_data["metadata"]["errors"]:
        logger.warning(f"Errors encountered: {patient_data['metadata']['errors']}")
    
    return patient_data

@app.get("/session/status/{session_id}")
async def session_status(session_id: str):
    """
    Session status endpoint - shows session info and token validity
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    current_time = time.time()
    expires_at = session.get("expires_at", 0)
    
    # Check token validity
    token_valid = current_time < expires_at
    time_remaining = max(0, expires_at - current_time)
    
    needs_reauth = session.get("needs_reauth", False)
    
    return {
        "session_id": session_id,
        "status": session.get("status"),
        "authenticated": session.get("status") == "authenticated",
        "needs_reauth": needs_reauth,
        "token_valid": token_valid and not needs_reauth,
        "token_info": {
            "has_access_token": bool(session.get("access_token")),
            "has_refresh_token": bool(session.get("refresh_token")),
            "expires_at": expires_at,
            "time_remaining": time_remaining,
            "expires_in_minutes": round(time_remaining / 60, 2)
        },
        "context": {
            "patient_id": session.get("patient_id"),
            "practitioner_id": session.get("practitioner_id"),
            "encounter_id": session.get("encounter_id")
        },
        "fhir_server": session.get("fhir_base"),
        "created_at": session.get("created_at"),
        "last_accessed": session.get("last_accessed"),
        "links": {
            "patient_data": f"/patient-data/{session_id}",
            "session_info": f"/session/{session_id}",
            "context_discovery": f"/context-discovery/{session_id}",
            "reauth_check": f"/reauth-required/{session_id}",
            "frontend": f"http://localhost:3002?token={session_id}" + ("&reauth=true" if needs_reauth else "")
        }
    }

@app.get("/reauth-required/{session_id}")
async def reauth_required(session_id: str):
    """
    Check if session requires re-authentication
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    needs_reauth = session.get("needs_reauth", False)
    
    return {
        "session_id": session_id,
        "needs_reauth": needs_reauth,
        "message": "Session requires re-authentication" if needs_reauth else "Session is valid",
        "launch_url": f"/launch?iss={session.get('fhir_base', '')}&launch={session.get('launch', '')}" if needs_reauth else None,
        "frontend_url": f"http://localhost:3002?token={session_id}&reauth=true" if needs_reauth else f"http://localhost:3002?token={session_id}"
    }

@app.post("/clear-reauth/{session_id}")
async def clear_reauth(session_id: str):
    """
    Clear the re-authentication flag (for testing)
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    session["needs_reauth"] = False
    session["last_accessed"] = time.time()
    
    logger.info(f"Re-authentication flag cleared for session {session_id}")
    
    return {
        "message": "Re-authentication flag cleared",
        "session_id": session_id,
        "needs_reauth": False
    }

@app.get("/fhir-resource/{session_id}/{resource_type}")
async def get_fhir_resource(session_id: str, resource_type: str):
    """
    Fetch a specific FHIR resource type using the stored access token
    Supported resource types: Patient, Observation, Encounter, MedicationRequest, DiagnosticReport
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    access_token = session.get("access_token")
    iss = session.get("fhir_base")
    
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token available")
    
    # Validate resource type
    valid_resources = ["Patient", "Observation", "Encounter", "MedicationRequest", "DiagnosticReport", "Procedure"]
    if resource_type not in valid_resources:
        raise HTTPException(status_code=400, detail=f"Invalid resource type. Supported types: {valid_resources}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/fhir+json",
                "User-Agent": "SMART-on-FHIR-Prototype/1.0"
            }
            
            # Build query parameters based on resource type
            query_params = ""
            if resource_type == "Observation":
                query_params = "?category=vital-signs&_sort=-date"
            elif resource_type == "Encounter":
                query_params = "?_sort=-date&_count=10"
            elif resource_type == "MedicationRequest":
                query_params = "?_sort=-date&_count=5"
            elif resource_type == "DiagnosticReport":
                query_params = "?_sort=-date&_count=5"
            elif resource_type == "Procedure":
                query_params = "?_sort=-date&_count=5"
            
            url = f"{iss}/{resource_type}{query_params}"
            logger.info(f"Fetching {resource_type} resource from {url}")
            
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched {resource_type} resource")
                return {
                    "resource_type": resource_type,
                    "data": data,
                    "metadata": {
                        "fhir_server": iss,
                        "session_id": session_id,
                        "total_results": data.get("total", 0),
                        "entry_count": len(data.get("entry", []))
                    }
                }
            else:
                error_msg = f"Failed to fetch {resource_type}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching {resource_type} resource: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch {resource_type} resource: {str(e)}")

@app.get("/fhir-search/{session_id}")
async def search_fhir_resources(session_id: str, resource_type: str = "Patient", query: str = ""):
    """
    Search FHIR resources with custom query parameters
    Example: /fhir-search/{session_id}?resource_type=Observation&query=category=vital-signs&_sort=-date
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    access_token = session.get("access_token")
    iss = session.get("fhir_base")
    
    if not access_token:
        raise HTTPException(status_code=401, detail="No access token available")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/fhir+json",
                "User-Agent": "SMART-on-FHIR-Prototype/1.0"
            }
            
            url = f"{iss}/{resource_type}"
            if query:
                url += f"?{query}"
            
            logger.info(f"Searching {resource_type} with query: {url}")
            
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Search completed for {resource_type}")
                return {
                    "resource_type": resource_type,
                    "query": query,
                    "data": data,
                    "metadata": {
                        "fhir_server": iss,
                        "session_id": session_id,
                        "total_results": data.get("total", 0),
                        "entry_count": len(data.get("entry", []))
                    }
                }
            else:
                error_msg = f"Search failed for {resource_type}: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=response.status_code, detail=error_msg)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching {resource_type} resources: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """
    Get session information (for debugging and monitoring)
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    
    # Return session info (excluding sensitive tokens for security)
    return {
        "session_id": session_id,
        "fhir_base": session.get("fhir_base"),
        "auth_endpoint": session.get("auth_endpoint"),
        "token_endpoint": session.get("token_endpoint"),
        "client_id": session.get("client_id"),
        "redirect_uri": session.get("redirect_uri"),
        "scope": session.get("scope"),
        "patient_id": session.get("patient_id"),
        "practitioner_id": session.get("practitioner_id"),
        "status": session.get("status"),
        "created_at": session.get("created_at"),
        "last_accessed": session.get("last_accessed"),
        "has_access_token": bool(session.get("access_token")),
        "has_refresh_token": bool(session.get("refresh_token")),
        "expires_at": session.get("expires_at")
    }

@app.get("/sessions")
async def list_sessions():
    """
    List all active sessions (for debugging and monitoring)
    """
    sessions_info = {}
    for session_id, session in SESSIONS.items():
        sessions_info[session_id] = {
            "fhir_base": session.get("fhir_base"),
            "status": session.get("status"),
            "patient_id": session.get("patient_id"),
            "practitioner_id": session.get("practitioner_id"),
            "created_at": session.get("created_at"),
            "last_accessed": session.get("last_accessed"),
            "has_access_token": bool(session.get("access_token"))
        }
    
    return {
        "total_sessions": len(SESSIONS),
        "sessions": sessions_info
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session (for cleanup)
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    del SESSIONS[session_id]
    logger.info(f"Session {session_id} deleted")
    
    return {"message": f"Session {session_id} deleted successfully"}

@app.get("/patient-select/{session_id}")
async def patient_select(session_id: str):
    """
    Patient selection endpoint for cases where no patient context was discovered
    This would typically redirect to a patient picker or show available patients
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    
    # Check if session is authenticated
    if session.get("status") != "authenticated":
        raise HTTPException(status_code=400, detail="Session not authenticated")
    
    # Check if patient context already exists
    if session.get("patient_id"):
        return {
            "message": "Patient context already exists",
            "patient_id": session.get("patient_id"),
            "redirect_url": f"http://localhost:3002?token={session_id}"
        }
    
    # For prototype, we'll return instructions for manual patient selection
    # In a real implementation, you might:
    # 1. Query the FHIR server for available patients
    # 2. Show a patient picker interface
    # 3. Allow the user to select a patient
    
    return {
        "message": "No patient context found - patient selection required",
        "session_id": session_id,
        "instructions": {
            "option_1": "Use SMART App Launcher to select a patient during launch",
            "option_2": "Manually specify patient ID via API",
            "option_3": "Implement patient picker interface"
        },
        "api_endpoint": f"/set-patient/{session_id}",
        "frontend_url": f"http://localhost:3002?token={session_id}&select_patient=true"
    }

@app.post("/set-patient/{session_id}")
async def set_patient(session_id: str, patient_id: str):
    """
    Manually set patient ID for a session (for testing/prototype)
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    
    # Check if session is authenticated
    if session.get("status") != "authenticated":
        raise HTTPException(status_code=400, detail="Session not authenticated")
    
    # Set patient ID
    session["patient_id"] = patient_id
    session["last_accessed"] = time.time()
    
    logger.info(f"Patient ID manually set for session {session_id}: {patient_id}")
    
    return {
        "message": "Patient ID set successfully",
        "session_id": session_id,
        "patient_id": patient_id,
        "redirect_url": f"http://localhost:3002?token={session_id}"
    }

@app.get("/context-discovery/{session_id}")
async def context_discovery(session_id: str):
    """
    Debug endpoint to show what context was discovered for a session
    """
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = SESSIONS[session_id]
    
    return {
        "session_id": session_id,
        "status": session.get("status"),
        "context_discovered": {
            "patient_id": session.get("patient_id"),
            "practitioner_id": session.get("practitioner_id"),
            "encounter_id": session.get("encounter_id")
        },
        "token_info": {
            "has_access_token": bool(session.get("access_token")),
            "has_refresh_token": bool(session.get("refresh_token")),
            "expires_at": session.get("expires_at"),
            "time_remaining": session.get("expires_at", 0) - time.time() if session.get("expires_at") else 0
        },
        "launch_context": {
            "launch": session.get("launch"),
            "fhir_base": session.get("fhir_base")
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
