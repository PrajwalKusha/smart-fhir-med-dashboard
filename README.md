# 🏥 SMART on FHIR Medical Dashboard

A comprehensive medical dashboard demonstrating SMART on FHIR integration with EHR systems. Built with FastAPI backend and Next.js frontend, featuring patient-specific health data visualization and OAuth2 authentication.

## ✨ Features

- **SMART on FHIR Integration** - Complete OAuth2 Authorization Code flow
- **Medical Dashboard** - Patient-specific health metrics, encounters, medications, and lab results
- **Patient Management** - Searchable patient selector with real-time filtering
- **Professional UI** - Healthcare-appropriate design with responsive layout
- **Real EHR Data** - Live data from SMART Health IT Sandbox

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd healthcare-app
   ```

2. **Start the Backend (Port 9001)**
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 9001
   ```

3. **Start the Frontend (Port 3002)**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access the Application**
   - Frontend: http://localhost:3002
   - Backend API: http://localhost:9001

## 🏗️ Architecture

```
healthcare-app/
├── backend/          # FastAPI backend
│   ├── main.py      # Core application logic
│   ├── config.py    # Configuration settings
│   └── requirements.txt
├── frontend/        # Next.js frontend
│   ├── app/         # Next.js app directory
│   ├── components/  # React components
│   └── package.json
└── README.md
```

## 🔐 SMART on FHIR Setup

1. **Visit SMART App Launcher**: https://launcher.smarthealthit.org/
2. **Configure your app**:
   - Launch URL: `http://localhost:9001/launch`
   - Redirect URI: `http://localhost:9001/callback`
   - Client ID: (auto-generated)
3. **Launch your app** using the generated URL

## 📊 Dashboard Features

- **Key Health Metrics** - Vital signs and health indicators
- **Recent Encounters** - Healthcare visits and appointments
- **Current Medications** - Active prescriptions and dosages
- **Lab Results** - Diagnostic reports and test results
- **Patient Search** - Find patients quickly with search functionality

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python, HTTPX
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **Integration**: SMART on FHIR, OAuth2, FHIR R4
- **Development**: Hot reload, TypeScript, ESLint

## 📝 API Endpoints

- `GET /launch` - SMART on FHIR launch endpoint
- `GET /callback` - OAuth2 callback handler
- `GET /patient-data/{session_id}` - Fetch patient data
- `GET /session/status/{session_id}` - Session information

## 🔧 Development

### Backend Development
```bash
cd backend
uvicorn main:app --reload --port 9001
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Production Build
```bash
cd frontend
npm run build
npm start
```

## 📚 Documentation

- [SMART on FHIR Documentation](http://docs.smarthealthit.org/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Create an issue in this repository
- Check the SMART on FHIR documentation
- Review the setup guide in `SMART_SANDBOX_SETUP.md`

---

**Built with ❤️ for healthcare innovation**