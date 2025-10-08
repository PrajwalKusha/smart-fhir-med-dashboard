# SMART Health IT Sandbox Setup Guide

This guide will help you configure the SMART Health IT Sandbox to test your SMART on FHIR application.

## Overview

The SMART Health IT Sandbox provides a simulated EHR environment where you can test SMART on FHIR applications without needing access to a real EHR system. It includes:

- Patient data simulation
- Provider/patient picker interface
- OAuth2 authorization flow
- FHIR R4 server with test data

## Step-by-Step Setup

### 1. Access the SMART App Launcher

1. Open your web browser and navigate to: https://launcher.smarthealthit.org/
2. You'll see the SMART App Launcher interface

### 2. Configure Your App

In the SMART App Launcher, you need to configure your application:

#### App Configuration:
- **App Name**: `SMART on FHIR Prototype`
- **Launch URL**: `http://localhost:9001/launch`
- **Redirect URI**: `http://localhost:9001/callback`
- **Client ID**: Leave empty (will be auto-generated) or use a custom value like `smart-fhir-prototype`
- **Scope**: `launch/patient patient/*.read patient/Patient.read patient/Observation.read patient/Encounter.read`

#### FHIR Server Selection:
- Choose **"SMART Health IT Sandbox"** from the dropdown
- This provides a public FHIR R4 server with test data

### 3. Generate Launch URL

After configuring your app:

1. Click **"Generate Launch URL"**
2. Copy the generated launch URL (it will look something like):
   ```
   https://launcher.smarthealthit.org/v/r4/sim/eyJhIjoiMSJ9/fhir-server-smart/launch?launch=eyJhIjoiMSJ9&iss=https%3A%2F%2Flauncher.smarthealthit.org%2Fv%2Fr4%2Ffhir
   ```

### 4. Update Your Backend Configuration

You need to update the client_id in your FastAPI backend to match what you configured:

1. Open `/backend/main.py`
2. Find the lines with `"client_id": "your-client-id"`
3. Replace `"your-client-id"` with the client ID you used in the launcher (or leave as auto-generated)

### 5. Test the Integration

1. **Start your backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --port 9001 --reload
   ```

2. **Start your frontend**:
   ```bash
   cd frontend
   npm install
   npm start
   ```

3. **Test the flow**:
   - Open http://localhost:3002
   - Click "Launch SMART App"
   - This will open the SMART App Launcher in a new tab
   - Use the generated launch URL from step 3
   - Complete the OAuth2 flow
   - You should be redirected back to your app with patient data

## Understanding the Launch Flow

### What Happens During Launch:

1. **EHR Simulation**: The sandbox simulates an EHR launching your app
2. **Launch Parameters**: Your app receives `launch` and `iss` parameters
3. **Patient/Provider Picker**: The sandbox may show a picker to select a patient
4. **OAuth2 Flow**: Your app redirects to the authorization server
5. **Token Exchange**: Authorization code is exchanged for an access token
6. **FHIR Data Access**: Your app uses the token to fetch patient data

### Launch Context Parameters:

The sandbox provides these context parameters:
- `launch`: Short-lived identifier for the launch session
- `iss`: Base URL of the FHIR server
- `patient`: Patient ID (when patient context is available)
- `practitioner`: Practitioner ID (when provider context is available)
- `encounter`: Encounter ID (when encounter context is available)

## Troubleshooting

### Common Issues:

1. **CORS Errors**: Make sure your backend is running on port 9001 and frontend on 3002
2. **Client ID Mismatch**: Ensure the client_id in your backend matches the launcher configuration
3. **Redirect URI Mismatch**: The redirect URI must exactly match what you configured
4. **Port Conflicts**: Make sure ports 9001 and 3002 are available

### Debug Tips:

1. **Check Backend Logs**: Look at the console output from your FastAPI server
2. **Network Tab**: Use browser developer tools to inspect network requests
3. **FHIR Server Metadata**: You can check the FHIR server capabilities at `{iss}/metadata`

### Testing Different Scenarios:

1. **Different Patients**: The sandbox allows you to select different patients
2. **Different Providers**: You can test with different practitioner contexts
3. **Different Encounters**: Test various encounter types and scenarios

## Advanced Configuration

### Custom FHIR Servers:

You can also test with other FHIR servers:
- **HAPI FHIR**: Public test server
- **Firely**: Community server
- **Your own server**: If you have a FHIR server running locally

### Additional Scopes:

For more comprehensive testing, you can request additional scopes:
- `patient/MedicationRequest.read`
- `patient/DiagnosticReport.read`
- `patient/Procedure.read`
- `user/*.read` (for user-level data)

## Next Steps

Once you have the basic flow working:

1. **Enhance the UI**: Improve the patient data display
2. **Add More Resources**: Fetch additional FHIR resources
3. **Error Handling**: Implement comprehensive error handling
4. **Security**: Add proper session management and security measures
5. **Deployment**: Deploy to a public URL for testing with real EHR systems

## Resources

- [SMART on FHIR Documentation](http://hl7.org/fhir/smart-app-launch/)
- [SMART Health IT](https://smarthealthit.org/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [OAuth2 Authorization Code Flow](https://tools.ietf.org/html/rfc6749#section-4.1)
