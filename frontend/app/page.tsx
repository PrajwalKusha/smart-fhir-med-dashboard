'use client'

import { useState, useEffect } from 'react'
import { 
  Heart, 
  Activity, 
  User, 
  Calendar, 
  Stethoscope, 
  Shield, 
  AlertCircle,
  CheckCircle,
  RefreshCw,
  ExternalLink,
  Eye,
  EyeOff,
  TrendingUp,
  Clock,
  Thermometer,
  Droplets,
  ChevronDown,
  Download,
  Filter
} from 'lucide-react'
import axios from 'axios'

interface Patient {
  id: string
  name: string
  gender: string
  birthDate: string
}

interface Observation {
  name: string
  value: string
  date: string
}

interface Encounter {
  type: string
  reason: string
  startDate: string
  endDate: string
}

interface PatientData {
  patient: {
    entry: Array<{
      resource: Patient
    }>
  }
  observations: {
    entry: Array<{
      resource: any
    }>
  }
  encounters: {
    entry: Array<{
      resource: any
    }>
  }
  medications?: {
    entry: Array<{
      resource: any
    }>
  }
  diagnostic_reports?: {
    entry: Array<{
      resource: any
    }>
  }
  metadata?: {
    fhir_server: string
    session_id: string
    resources_fetched: string[]
    errors: string[]
  }
}

export default function Home() {
  const [patientData, setPatientData] = useState<PatientData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [showRawData, setShowRawData] = useState(false)
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [showPatientSelector, setShowPatientSelector] = useState(false)
  const [patientSearchTerm, setPatientSearchTerm] = useState('')

  // Check for session ID in URL parameters on component mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const token = urlParams.get('token')
    if (token) {
      setSessionId(token)
      fetchPatientData(token)
    }
  }, [])

  const launchSMARTApp = () => {
    const launcherUrl = 'https://launcher.smarthealthit.org/'
    window.open(launcherUrl, '_blank')
  }

  const fetchPatientData = async (sessionId: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await axios.get(`http://localhost:9001/patient-data/${sessionId}`)
      setPatientData(response.data)
    } catch (err: any) {
      setError('Failed to fetch patient data: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const formatPatientName = (patient: any): string => {
    if (!patient || !patient.name || patient.name.length === 0) {
      return 'Unknown'
    }
    
    const name = patient.name[0]
    const given = name.given ? name.given.join(' ') : ''
    const family = name.family || ''
    const fullName = `${given} ${family}`.trim()
    
    return fullName
  }

  const formatObservation = (obs: any): Observation => {
    if (!obs.code || !obs.code.coding || obs.code.coding.length === 0) {
      return { name: 'Unknown', value: 'N/A', date: 'Unknown' }
    }
    
    const coding = obs.code.coding[0]
    const display = coding.display || coding.code || 'Unknown'
    
    let value = 'N/A'
    if (obs.valueQuantity) {
      // Format numeric values to reasonable precision
      const numericValue = parseFloat(obs.valueQuantity.value)
      const formattedValue = isNaN(numericValue) ? obs.valueQuantity.value : numericValue.toFixed(2)
      value = `${formattedValue} ${obs.valueQuantity.unit || ''}`
    } else if (obs.valueString) {
      value = obs.valueString
    }
    
    return {
      name: display,
      value: value,
      date: obs.effectiveDateTime || obs.issued || 'Unknown'
    }
  }

  const formatEncounter = (encounter: any): Encounter => {
    const type = encounter.type && encounter.type.length > 0 
      ? encounter.type[0].text || encounter.type[0].coding?.[0]?.display || 'Unknown'
      : 'Unknown'
    
    const reason = encounter.reasonCode && encounter.reasonCode.length > 0
      ? encounter.reasonCode[0].text || encounter.reasonCode[0].coding?.[0]?.display || 'Unknown'
      : 'Not specified'
    
    const startDate = encounter.period?.start || 'Unknown'
    const endDate = encounter.period?.end || 'Ongoing'
    
    return {
      type,
      reason,
      startDate,
      endDate
    }
  }

  const formatMedication = (medication: any) => {
    const medicationName = medication.medicationCodeableConcept?.text || 
                          medication.medicationCodeableConcept?.coding?.[0]?.display || 
                          'Unknown Medication'
    
    const status = medication.status || 'Unknown'
    const dosage = medication.dosageInstruction?.[0]?.text || 'Not specified'
    const prescribedDate = medication.authoredOn || 'Unknown'
    
    return {
      name: medicationName,
      status,
      dosage,
      prescribedDate
    }
  }

  const formatDiagnosticReport = (report: any) => {
    const code = report.code?.coding?.[0]?.display || 
                report.code?.text || 
                'Unknown Test'
    
    const status = report.status || 'Unknown'
    const effectiveDate = report.effectiveDateTime || report.issued || 'Unknown'
    const conclusion = report.conclusion || 'No conclusion available'
    
    return {
      code,
      status,
      effectiveDate,
      conclusion
    }
  }

  // Get current vital signs for the selected patient
  const getCurrentVitals = () => {
    if (!patientData?.observations?.entry || !selectedPatient) return []
    
    const filteredObservations = patientData.observations.entry.filter(entry => {
      const subjectRef = entry.resource.subject?.reference
      return subjectRef?.includes(selectedPatient.id)
    })
    
    const vitals = filteredObservations
      .map(entry => formatObservation(entry.resource))
      .filter(obs => obs.name && obs.value !== 'N/A')
      .slice(0, 6) // Show top 6 most recent vitals
    
    return vitals
  }

  // Get recent encounters for the selected patient
  const getRecentEncounters = () => {
    if (!patientData?.encounters?.entry || !selectedPatient) return []
    
    const filteredEncounters = patientData.encounters.entry.filter(entry => {
      const subjectRef = entry.resource.subject?.reference
      return subjectRef?.includes(selectedPatient.id)
    })
    
    return filteredEncounters
      .map(entry => formatEncounter(entry.resource))
      .slice(0, 5) // Show last 5 encounters
  }

  // Get available patients for selector
  const getAvailablePatients = () => {
    if (!patientData?.patient?.entry) return []
    
    return patientData.patient.entry.map(entry => ({
      id: entry.resource.id,
      name: formatPatientName(entry.resource),
      gender: entry.resource.gender || 'Unknown',
      birthDate: entry.resource.birthDate || 'Unknown'
    }))
  }

  // Get all unique patient IDs from FHIR resources
  const getAllPatientIds = () => {
    const patientIds = new Set()
    
    // Get patient IDs from observations
    if (patientData?.observations?.entry) {
      patientData.observations.entry.forEach(entry => {
        const subjectRef = entry.resource.subject?.reference
        if (subjectRef && subjectRef.startsWith('Patient/')) {
          patientIds.add(subjectRef.replace('Patient/', ''))
        }
      })
    }
    
    // Get patient IDs from encounters
    if (patientData?.encounters?.entry) {
      patientData.encounters.entry.forEach(entry => {
        const subjectRef = entry.resource.subject?.reference
        if (subjectRef && subjectRef.startsWith('Patient/')) {
          patientIds.add(subjectRef.replace('Patient/', ''))
        }
      })
    }
    
    // Get patient IDs from medications
    if (patientData?.medications?.entry) {
      patientData.medications.entry.forEach(entry => {
        const subjectRef = entry.resource.subject?.reference
        if (subjectRef && subjectRef.startsWith('Patient/')) {
          patientIds.add(subjectRef.replace('Patient/', ''))
        }
      })
    }
    
    // Get patient IDs from diagnostic reports
    if (patientData?.diagnostic_reports?.entry) {
      patientData.diagnostic_reports.entry.forEach(entry => {
        const subjectRef = entry.resource.subject?.reference
        if (subjectRef && subjectRef.startsWith('Patient/')) {
          patientIds.add(subjectRef.replace('Patient/', ''))
        }
      })
    }
    
    return Array.from(patientIds)
  }

  // Get filtered and limited patients for dropdown
  const getFilteredPatients = () => {
    const patientIds = getAllPatientIds()
    const patients = patientIds.map(patientId => {
      const patientInfo = patientData?.patient?.entry?.find(entry => entry.resource.id === patientId)
      const patientName = patientInfo ? formatPatientName(patientInfo.resource) : `Patient ${patientId}`
      const patientGender = patientInfo?.resource.gender || 'Unknown'
      const patientBirthDate = patientInfo?.resource.birthDate || 'Unknown'
      
      return {
        id: patientId,
        name: patientName,
        gender: patientGender,
        birthDate: patientBirthDate
      }
    })

    // Filter by search term
    const filtered = patients.filter(patient => 
      patient.name.toLowerCase().includes(patientSearchTerm.toLowerCase()) ||
      patient.id.toLowerCase().includes(patientSearchTerm.toLowerCase())
    )

    // Limit to 10 results
    return filtered.slice(0, 10)
  }

  // Get medications for the selected patient
  const getPatientMedications = () => {
    if (!patientData?.medications?.entry || !selectedPatient) return []
    
    return patientData.medications.entry
      .filter(entry => entry.resource.subject?.reference?.includes(selectedPatient.id))
      .slice(0, 6)
  }

  // Get lab results for the selected patient
  const getPatientLabResults = () => {
    if (!patientData?.diagnostic_reports?.entry || !selectedPatient) return []
    
    return patientData.diagnostic_reports.entry
      .filter(entry => entry.resource.subject?.reference?.includes(selectedPatient.id))
      .slice(0, 5)
  }

  // Auto-select first patient when data loads
  useEffect(() => {
    if (patientData && !selectedPatient) {
      const patientIds = getAllPatientIds()
      
      if (patientIds.length > 0) {
        const firstPatientId = patientIds[0]
        const patientInfo = patientData?.patient?.entry?.find(entry => entry.resource.id === firstPatientId)
        
        // If patient info not found, try to use the first available patient
        let finalPatientInfo = patientInfo
        let finalPatientId = firstPatientId
        
        if (!patientInfo && patientData?.patient?.entry?.length > 0) {
          finalPatientInfo = patientData.patient.entry[0]
          finalPatientId = finalPatientInfo.resource.id
        }
        
        const patientName = finalPatientInfo ? formatPatientName(finalPatientInfo.resource) : `Patient ${finalPatientId}`
        const patientGender = finalPatientInfo?.resource.gender || 'Unknown'
        const patientBirthDate = finalPatientInfo?.resource.birthDate || 'Unknown'
        
        setSelectedPatient({
          id: finalPatientId,
          name: patientName,
          gender: patientGender,
          birthDate: patientBirthDate
        })
      }
    }
  }, [patientData, selectedPatient])

  // Close patient selector when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showPatientSelector) {
        const target = event.target as HTMLElement
        if (!target.closest('.patient-selector')) {
          setShowPatientSelector(false)
          setPatientSearchTerm('')
        }
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showPatientSelector])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Header */}
      <header className="bg-white shadow-soft border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-100 rounded-lg">
                <Stethoscope className="h-6 w-6 text-primary-600" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">SMART on FHIR</h1>
                <p className="text-sm text-gray-600">EHR Integration Prototype</p>
              </div>
            </div>
            
            {sessionId && (
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-5 w-5 text-success-600" />
                <span className="text-sm font-medium text-success-700">Connected</span>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Launch Section */}
        {!sessionId && (
          <div className="text-center mb-12">
            <div className="card max-w-2xl mx-auto">
              <div className="text-center">
                <div className="p-4 bg-primary-100 rounded-full w-16 h-16 mx-auto mb-6 flex items-center justify-center">
                  <Shield className="h-8 w-8 text-primary-600" />
                </div>
                <h2 className="text-3xl font-bold text-gray-900 mb-4">
                  Launch SMART Application
                </h2>
                <p className="text-lg text-gray-600 mb-8">
                  This application demonstrates SMART on FHIR integration with EHR systems.
                  Click the button below to open the SMART App Launcher and test the OAuth2 flow.
                </p>
                <button 
                  onClick={launchSMARTApp}
                  className="btn btn-primary text-lg px-8 py-3"
                >
                  <ExternalLink className="h-5 w-5 mr-2" />
                  Launch SMART App
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="card border-l-4 border-danger-500 bg-danger-50 mb-6">
            <div className="flex items-center">
              <AlertCircle className="h-5 w-5 text-danger-600 mr-3" />
              <div>
                <h3 className="text-sm font-medium text-danger-800">Error</h3>
                <p className="text-sm text-danger-700 mt-1">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="card text-center py-12">
            <div className="loading-spinner mx-auto mb-4"></div>
            <p className="text-gray-600">Loading patient data...</p>
          </div>
        )}

        {/* Medical Dashboard */}
        {patientData && (
          <div className="space-y-8">
            {/* Patient Header */}
            <div className="bg-white rounded-xl shadow-soft p-6">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-gray-900 mb-2">Medical Dashboard</h2>
                  <p className="text-gray-600">Comprehensive patient health overview</p>
                </div>
                <div className="flex space-x-3">
                  <button 
                    onClick={() => sessionId && fetchPatientData(sessionId)}
                    disabled={loading}
                    className="btn btn-primary"
                  >
                    <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                    Refresh Data
                  </button>
                  <button 
                    onClick={() => setShowRawData(!showRawData)}
                    className="btn btn-secondary"
                  >
                    {showRawData ? <EyeOff className="h-4 w-4 mr-2" /> : <Eye className="h-4 w-4 mr-2" />}
                    {showRawData ? 'Hide' : 'Show'} Raw Data
                  </button>
                </div>
              </div>

              {/* Patient Selector */}
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <User className="h-5 w-5 text-gray-600" />
                  <span className="text-sm font-medium text-gray-700">Patient:</span>
                </div>
                <div className="relative patient-selector">
                  <button
                    onClick={() => setShowPatientSelector(!showPatientSelector)}
                    className="flex items-center space-x-2 bg-gray-50 hover:bg-gray-100 px-4 py-2 rounded-lg border border-gray-200 transition-colors"
                  >
                    <span className="font-medium text-gray-900">
                      {selectedPatient ? (selectedPatient.name || `Patient ${selectedPatient.id}`) : 'Select Patient'}
                    </span>
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  </button>
                  
                  {showPatientSelector && (
                    <div className="absolute top-full left-0 mt-2 w-96 bg-white rounded-lg shadow-lg border border-gray-200 z-10">
                      <div className="p-4">
                        {/* Search Input */}
                        <div className="mb-3">
                          <input
                            type="text"
                            placeholder="Search patients..."
                            value={patientSearchTerm}
                            onChange={(e) => setPatientSearchTerm(e.target.value)}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                            autoFocus
                          />
                        </div>
                        
                        {/* Patient List */}
                        <div className="max-h-80 overflow-y-auto">
                          {getFilteredPatients().map((patient) => (
                            <button
                              key={patient.id}
                              onClick={() => {
                                setSelectedPatient(patient)
                                setShowPatientSelector(false)
                                setPatientSearchTerm('')
                              }}
                              className="w-full text-left p-3 hover:bg-gray-50 rounded-lg transition-colors border-b border-gray-100 last:border-b-0"
                            >
                              <div className="font-medium text-gray-900">{patient.name}</div>
                              <div className="text-sm text-gray-600">
                                {patient.gender} • Born {patient.birthDate}
                              </div>
                              <div className="text-xs text-gray-500">ID: {patient.id}</div>
                            </button>
                          ))}
                          
                          {getFilteredPatients().length === 0 && (
                            <div className="text-center py-4 text-gray-500">
                              No patients found matching "{patientSearchTerm}"
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Key Metrics Section */}
            {selectedPatient && (
              <div className="bg-white rounded-xl shadow-soft p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <TrendingUp className="h-6 w-6 text-primary-600" />
                  <h3 className="text-xl font-semibold text-gray-900">Key Health Metrics</h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                  {getCurrentVitals().map((vital, index) => (
                    <div key={index} className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-100 min-h-[120px] flex flex-col">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-xs font-medium text-gray-600 leading-tight line-clamp-2">{vital.name}</div>
                        <Activity className="h-4 w-4 text-blue-600 flex-shrink-0 ml-1" />
                      </div>
                      <div className="flex-1 flex flex-col justify-center">
                        <div className="text-lg font-bold text-blue-700 mb-1 break-words">{vital.value}</div>
                        <div className="text-xs text-gray-500 truncate">{vital.date}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Encounters Section */}
            {selectedPatient && (
              <div className="bg-white rounded-xl shadow-soft p-6">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-2">
                    <Calendar className="h-6 w-6 text-warning-600" />
                    <h3 className="text-xl font-semibold text-gray-900">Recent Encounters</h3>
                  </div>
                  <span className="text-sm text-gray-500">Last 5 visits</span>
                </div>
                
                <div className="space-y-3">
                  {getRecentEncounters().map((encounter, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                      <div className="flex items-center space-x-4">
                        <div className="p-2 bg-warning-100 rounded-lg">
                          <Calendar className="h-4 w-4 text-warning-600" />
                        </div>
                        <div>
                          <div className="font-medium text-gray-900">{encounter.type}</div>
                          <div className="text-sm text-gray-600">{encounter.reason}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium text-gray-900">{encounter.startDate}</div>
                        <div className="text-xs text-gray-500">{encounter.endDate}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Additional Sections - Medications and Lab Results */}
            {selectedPatient && getPatientMedications().length > 0 && (
              <div className="bg-white rounded-xl shadow-soft p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <Heart className="h-6 w-6 text-primary-600" />
                  <h3 className="text-xl font-semibold text-gray-900">Current Medications</h3>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {getPatientMedications().map((entry, index) => {
                    const medication = entry.resource
                    const formatted = formatMedication(medication)
                    return (
                      <div key={index} className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-100">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-gray-900">{formatted.name}</h4>
                          <span className={`badge ${formatted.status === 'active' ? 'badge-success' : 'badge-warning'}`}>
                            {formatted.status}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 mb-2">{formatted.dosage}</div>
                        <div className="text-xs text-gray-500">Prescribed: {formatted.prescribedDate}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Lab Results */}
            {selectedPatient && getPatientLabResults().length > 0 && (
              <div className="bg-white rounded-xl shadow-soft p-6">
                <div className="flex items-center space-x-2 mb-6">
                  <Activity className="h-6 w-6 text-info-600" />
                  <h3 className="text-xl font-semibold text-gray-900">Recent Lab Results</h3>
                </div>
                <div className="space-y-4">
                  {getPatientLabResults().map((entry, index) => {
                    const report = entry.resource
                    const formatted = formatDiagnosticReport(report)
                    return (
                      <div key={index} className="bg-gradient-to-br from-cyan-50 to-blue-50 rounded-lg p-4 border border-cyan-100">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium text-gray-900">{formatted.code}</h4>
                          <span className={`badge ${formatted.status === 'final' ? 'badge-success' : 'badge-warning'}`}>
                            {formatted.status}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 mb-2">{formatted.conclusion}</div>
                        <div className="text-xs text-gray-500">Date: {formatted.effectiveDate}</div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Raw Data Debug View */}
            {showRawData && (
              <div className="card">
                <div className="card-header">
                  <h3 className="text-xl font-semibold text-gray-900">Raw FHIR Data (Debug)</h3>
                </div>
                <div className="bg-gray-900 rounded-lg p-4 overflow-auto max-h-96">
                  <pre className="text-sm text-green-400">
                    {JSON.stringify(patientData, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
