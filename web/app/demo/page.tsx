'use client'

import { AppHeader, PageIntro } from '../../components/app-header'
import { useState, useEffect, useRef } from 'react'
import { 
  Upload, 
  Sparkles, 
  Download, 
  Eye, 
  X, 
  Plus, 
  Trash2, 
  Users, 
  FileText, 
  Settings,
  LogOut,
  User,
  Shield,
  CheckCircle,
  AlertCircle,
  Calendar,
  Building,
  PenTool,
  Target,
  BookOpen,
  Loader,
  Lock,
  Zap
} from 'lucide-react'
import { apiClient } from '../../lib/api'
import { Document, CustomRule, FirmDetails } from '../../lib/api'
import Link from 'next/link'

interface ProcessingStep {
  id: string
  name: string
  status: 'pending' | 'processing' | 'completed' | 'error'
  progress: number
  details?: string
}

export default function DemoPage() {
  // Demo state - no authentication required
  const [userId, setUserId] = useState('1') // Default to admin (ID: 1)
  const [userRole, setUserRole] = useState('admin') // Default to admin role
  const [signatureFile, setSignatureFile] = useState<File | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)
  const [showPreview, setShowPreview] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  
  // Role-specific document states
  const [adminUploadedFile, setAdminUploadedFile] = useState<File | null>(null)
  const [adminUploadedDocument, setAdminUploadedDocument] = useState<Document | null>(null)
  const [adminProcessingResult, setAdminProcessingResult] = useState<any>(null)
  
  const [userUploadedFile, setUserUploadedFile] = useState<File | null>(null)
  const [userUploadedDocument, setUserUploadedDocument] = useState<Document | null>(null)
  const [userProcessingResult, setUserProcessingResult] = useState<any>(null)
  
  const [customRules, setCustomRules] = useState<CustomRule[]>([
    {
      instruction: 'Change term length to 2 years if longer than 2 years',
      category: 'term'
    },
    {
      instruction: 'Include investors, potential financing sources, and agents if not included',
      category: 'parties'
    },
    {
      instruction: 'Cap confidentiality obligations at 18 months',
      category: 'term'
    },
    {
      instruction: 'Limit liability to actual damages, exclude consequential damages',
      category: 'other'
    }
  ])

  const [firmDetails, setFirmDetails] = useState<FirmDetails>({
    name: 'Your Law Firm LLC',
    address: '123 Business Street',
    city: 'New York',
    state: 'NY',
    zipCode: '10001',
    signerName: 'John Smith',
    signerTitle: 'Managing Partner',
    email: 'john.smith@yourfirm.com',
    phone: '(555) 123-4567'
  })

  const [processingSteps] = useState<ProcessingStep[]>([
    { 
      id: 'upload', 
      name: 'Document Analysis & Validation', 
      status: 'pending', 
      progress: 0,
      details: 'Analyzing NDA structure and content'
    },
    { 
      id: 'rules', 
      name: userRole === 'admin' ? 'Applying Custom Instructions' : 'Standard Processing', 
      status: 'pending', 
      progress: 0,
      details: userRole === 'admin' ? 'Processing user-defined redlining rules' : 'Using standard legal practices'
    },
    { 
      id: 'ai', 
      name: 'AI-Powered Redlining', 
      status: 'pending', 
      progress: 0,
      details: 'AI agent applying intelligent modifications'
    },
    { 
      id: 'firm', 
      name: 'Inserting Firm Details', 
      status: 'pending', 
      progress: 0,
      details: 'Adding firm information and signature blocks'
    },
    { 
      id: 'output', 
      name: 'Generating Redlined Document', 
      status: 'pending', 
      progress: 0,
      details: 'Creating final Word document with tracked changes'
    }
  ])

  const [newRule, setNewRule] = useState('')
  const [newRuleCategory, setNewRuleCategory] = useState('other')
  const [showAdminRuleModal, setShowAdminRuleModal] = useState(false)
  const [adminRuleName, setAdminRuleName] = useState('')
  const [adminRuleInstruction, setAdminRuleInstruction] = useState('')
  const [adminRuleCategory, setAdminRuleCategory] = useState('other')
  const [showAddUserModal, setShowAddUserModal] = useState(false)
  const [newUserData, setNewUserData] = useState({
    username: '',
    email: '',
    role: 'USER',
    password: ''
  })
  const adminRuleModalRef = useRef<HTMLDivElement>(null)
  const addUserModalRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Check authentication on component mount
  useEffect(() => {
    // No authentication check needed for demo
  }, [])

  // Redirect if not authenticated
  // No redirect needed for demo

  // Handle click outside modals to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node
      
      if (showAdminRuleModal && adminRuleModalRef.current && !adminRuleModalRef.current.contains(target)) {
        setShowAdminRuleModal(false)
      }
      if (showAddUserModal && addUserModalRef.current && !addUserModalRef.current.contains(target)) {
        setShowAddUserModal(false)
      }
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setShowAdminRuleModal(false)
        setShowAddUserModal(false)
      }
    }

    if (showAdminRuleModal || showAddUserModal) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [showAdminRuleModal, showAddUserModal])

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file && file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
      if (userRole === 'admin') {
        setAdminUploadedFile(file)
        setUserUploadedFile(null) // Clear user file when admin uploads
      } else {
        setUserUploadedFile(file)
        setAdminUploadedFile(null) // Clear admin file when user uploads
      }
      setError(null)
    } else {
      setError('Please select a valid .docx file')
    }
  }

  const handleSignatureUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      // This state is not used in the current logic, but kept for potential future use
      // setSignatureFile(file) 
    }
  }

  const addCustomRule = () => {
    if (newRule.trim()) {
      const rule: CustomRule = {
        instruction: newRule.trim(),
        category: newRuleCategory
      }
      setCustomRules(prev => [...prev, rule])
      setNewRule('')
      setNewRuleCategory('other')
    }
  }

  const removeCustomRule = (index: number) => {
    setCustomRules(prev => prev.filter((_, i) => i !== index))
  }

  const createAdminRule = async () => {
    if (!adminRuleName.trim() || !adminRuleInstruction.trim()) {
      setError('Rule name and instruction are required')
      return
    }

    try {
      // For demo purposes, add to local state
      const newRule: CustomRule = {
        name: adminRuleName,
        category: adminRuleCategory,
        instruction: adminRuleInstruction
      }
      
      setCustomRules(prev => [...prev, newRule])
      
      // Clear form and close modal
      setAdminRuleName('')
      setAdminRuleInstruction('')
      setAdminRuleCategory('other')
      setShowAdminRuleModal(false)
      
      // Show success message
      setError(null)
      setSuccess('Rule created successfully!')
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      setError(err.message || 'Failed to create rule')
    }
  }

  const addNewUser = async () => {
    if (!newUserData.username.trim() || !newUserData.email.trim() || !newUserData.password.trim()) {
      setError('Username, email, and password are required')
      return
    }

    try {
      // For demo purposes, show success message
      setError(null)
      setSuccess(`User "${newUserData.username}" created successfully!`)
      
      // Clear form and close modal
      setNewUserData({
        username: '',
        email: '',
        role: 'USER',
        password: ''
      })
      setShowAddUserModal(false)
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), 3000)
    } catch (err: any) {
      setError(err.message || 'Failed to create user')
    }
  }

  const updateFirmDetails = (field: keyof FirmDetails, value: string) => {
    setFirmDetails(prev => ({ ...prev, [field]: value }))
  }

  const uploadDocument = async (): Promise<Document | null> => {
    const currentFile = getCurrentUploadedFile()
    if (!currentFile) return null

    try {
      if (!userId) {
        throw new Error('User ID not set')
      }
      const result = await apiClient.uploadDocument(currentFile, userId)
      return result.document
    } catch (err: any) {
      setError(err.message || 'Failed to upload document')
      return null
    }
  }

  const startProcessing = async () => {
    const currentFile = getCurrentUploadedFile()
    if (!currentFile) return
    
    setIsProcessing(true)
    setCurrentStep(0)
    setError(null)
    
    try {
      // Step 1: Upload document
      setCurrentStep(0)
      const document = await uploadDocument()
      if (!document) {
        throw new Error('Failed to upload document')
      }
      
      // Update role-specific document state
      if (userRole === 'admin') {
        setAdminUploadedDocument(document)
      } else {
        setUserUploadedDocument(document)
      }
      
      // Step 2: Determine rules to use based on user role
      setCurrentStep(1)
      let rulesToUse: CustomRule[] = []
      
      if (userRole === 'admin') {
        // Admins can use their custom rules
        rulesToUse = customRules
      }
      // Regular users get no rules (empty array)
      
      // Step 3: Process document with AI
      setCurrentStep(2)
      
      const result = await apiClient.processDocument(
        document.id,
        rulesToUse,
        firmDetails,
        userId
      )
      
      // Update the role-specific document state with the processing result
      if (result.document) {
        if (userRole === 'admin') {
          setAdminUploadedDocument(result.document)
        } else {
          setUserUploadedDocument(result.document)
        }
      }
      
      // Update role-specific processing result
      if (userRole === 'admin') {
        setAdminProcessingResult(result.processing_result)
      } else {
        setUserProcessingResult(result.processing_result)
      }
      
      setCurrentStep(4) // Mark as completed
      
      // Wait a moment to show completion
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      setIsProcessing(false)
      setShowPreview(true)
      
    } catch (err: any) {
      setError(err.message || 'Processing failed')
      setIsProcessing(false)
      setCurrentStep(0)
    }
  }

  const downloadDocument = async () => {
    const currentDoc = getCurrentUploadedDocument()
    if (!currentDoc?.output_path) {
      setError('Run the review to get a download')
      return
    }

    try {
      if (!userId) {
        throw new Error('User ID not set')
      }
      await apiClient.downloadDocument(currentDoc.id, userId)
    } catch (err: any) {
      setError(`Download failed: ${err.message}`)
    }
  }

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'term': return <Calendar className="w-4 h-4 text-fg-2" />
      case 'parties': return <Users className="w-4 h-4 text-fg-2" />
      case 'firm': return <Building className="w-4 h-4 text-fg-2" />
      case 'signature': return <PenTool className="w-4 h-4 text-fg-2" />
      default: return <Target className="w-4 h-4 text-fg-2" />
    }
  }

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'term': return 'Term'
      case 'parties': return 'Parties'
      case 'firm': return 'Firm details'
      case 'signature': return 'Signature'
      default: return 'Other'
    }
  }

  const getCurrentUploadedFile = () => {
    return userRole === 'admin' ? adminUploadedFile : userUploadedFile;
  }

  const clearCurrentUploadedFile = () => {
    if (userRole === 'admin') {
      setAdminUploadedFile(null);
    } else {
      setUserUploadedFile(null);
    }
  }

  const getCurrentUploadedDocument = () => {
    return userRole === 'admin' ? adminUploadedDocument : userUploadedDocument;
  }

  const getCurrentProcessingResult = () => {
    return userRole === 'admin' ? adminProcessingResult : userProcessingResult;
  }

  const clearAllState = () => {
    // Clear all document and processing state
    setAdminUploadedFile(null)
    setAdminUploadedDocument(null)
    setAdminProcessingResult(null)
    setUserUploadedFile(null)
    setUserUploadedDocument(null)
    setUserProcessingResult(null)
    setIsProcessing(false)
    setCurrentStep(0)
    setShowPreview(false)
    setError(null)
    setSuccess(null)
    
    // Clear the file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleLogout = () => {
    // No logout functionality in demo
  }

  return (
    <div className="min-h-screen bg-black text-white/90">
      {/* Header */}
      <AppHeader section="Demo">
        <label htmlFor="demo-role" className="hidden text-[0.9rem] text-fg-2 md:block">View as</label>
        <select
          id="demo-role"
          value={userId}
          onChange={(e) => {
            const newUserId = e.target.value
            setUserId(newUserId)
            setUserRole(newUserId === '1' ? 'admin' : 'user')
            clearAllState()
          }}
          className="field !h-10 !w-auto !rounded-full !px-4 !text-[0.9rem]"
        >
          <option value="1">Admin</option>
          <option value="2">Reviewer</option>
        </select>
        <Link href="/" className="hidden text-[0.95rem] text-fg-2 hover:text-white md:block">Back to site</Link>
      </AppHeader>

      <div className="mx-auto max-w-[1400px] px-5 py-12 md:px-8 md:py-16">
        <PageIntro title="Try a redline">Upload an NDA, pick or write rules, and get back a Word file with tracked changes. Switch between the admin and reviewer views from the header.</PageIntro>

        {/* Error Display */}
        {error && (
          <div className="mb-8 bg-redline-wash border border-redline/50 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-redline-text" />
              <span className="text-redline-text">{error}</span>
            </div>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="mb-8 bg-ok-wash border border-ok/40 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-ok" />
              <span className="text-ok">{success}</span>
            </div>
          </div>
        )}

        {/* Admin Section - Only visible to admins */}
        {userRole === 'admin' && (
          <div className="mb-8 panel p-6">
            <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
              <Users className="w-5 h-5 mr-2 text-metal-mid" />
              Team and rules
            </h2>
            
            <div className="grid md:grid-cols-2 gap-6">
              {/* System Statistics */}
              <div className="bg-ink-panel rounded-lg p-4">
                <h3 className="text-lg font-medium text-white mb-3">Overview</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-fg-2">Users</span>
                    <span className="text-white">2</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-fg-2">Documents</span>
                    <span className="text-white">-</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-fg-2">Rules</span>
                    <span className="text-white">{customRules.length}</span>
                  </div>
                </div>
              </div>
              
              {/* Shortcuts */}
              <div className="bg-ink-panel rounded-lg p-4">
                <h3 className="text-lg font-medium text-white mb-3">Shortcuts</h3>
                <div className="space-y-2">
                  <button 
                    onClick={() => setShowAdminRuleModal(true)}
                    className="btn-metal sm w-full"
                  >
                    Add a rule for everyone
                  </button>
                  <button 
                    onClick={() => setShowAddUserModal(true)}
                    className="btn-metal sm w-full"
                  >
                    Add a user
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column - Upload & Configuration */}
          <div className="space-y-8">
            {/* File Upload */}
            <div className="panel p-6">
              <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                <Upload className="w-5 h-5 mr-2 text-metal-mid" />
                Upload the NDA
              </h2>
              
              {!getCurrentUploadedFile() ? (
                <div className="border-2 border-dashed border-line rounded-lg p-8 text-center hover:border-line-strong transition-colors">
                  <input
                    type="file"
                    accept=".docx"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="file-upload"
                    ref={fileInputRef}
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Upload className="w-12 h-12 mx-auto mb-4 text-metal-mid" />
                    <p className="text-lg font-medium text-white mb-2">Drop your NDA here</p>
                    <p className="text-fg-2">or click to browse</p>
                    <p className="text-sm text-fg-3 mt-2">Word .docx files only</p>
                  </label>
                </div>
              ) : (
                <div className="bg-white/5 rounded-lg p-4 border border-line">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-8 h-8 text-metal-mid" />
                    <div className="flex-1">
                      <p className="font-medium text-white">{getCurrentUploadedFile()?.name}</p>
                      <p className="text-sm text-fg-2">
                        {getCurrentUploadedFile() ? (getCurrentUploadedFile()!.size / 1024 / 1024).toFixed(2) : 0} MB
                      </p>
                    </div>
                    <button
                      onClick={() => clearCurrentUploadedFile()}
                      className="text-fg-2 hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Custom Rules - Only visible to admins */}
            {userRole === 'admin' && (
              <div className="panel p-6">
                <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                  <Shield className="w-5 h-5 mr-2 text-metal-mid" />
                  Rules
                </h2>
                
                <div className="space-y-4">
                  <div className="flex space-x-3">
                    <select
                      value={newRuleCategory}
                      onChange={(e) => setNewRuleCategory(e.target.value)}
                      className="flex-1 bg-ink-panel border border-line rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-white/15"
                    >
                      <option value="term">Term</option>
                      <option value="parties">Parties</option>
                      <option value="firm">Firm Details</option>
                      <option value="signature">Signature</option>
                      <option value="other">Other</option>
                    </select>
                    <input
                      type="text"
                      value={newRule}
                      onChange={(e) => setNewRule(e.target.value)}
                      placeholder="Enter redlining instruction..."
                      className="field flex-1"
                    />
                    <button
                      onClick={addCustomRule}
                      className="btn-metal sm"
                    >
                      Add rule
                    </button>
                  </div>
                  
                  {/* Display custom rules */}
                  {customRules.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-medium text-fg-2">Active rules</h3>
                      {customRules.map((rule, index) => (
                        <div key={index} className="flex items-center justify-between bg-ink-panel rounded-lg p-3">
                          <div className="flex items-center space-x-3">
                            {getCategoryIcon(rule.category)}
                            <div>
                              {rule.name && (
                                <div className="text-sm font-medium text-white">{rule.name}</div>
                              )}
                              <span className="text-sm text-white/90">{rule.instruction}</span>
                            </div>
                          </div>
                          <button
                            onClick={() => removeCustomRule(index)}
                            className="text-redline-text hover:text-white transition-colors"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Rules Display - Shows custom rules created by admin */}
            <div className="panel p-6">
              <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                <BookOpen className="w-5 h-5 mr-2 text-metal-mid" />
                Rule library
              </h2>
              
              {customRules.length > 0 ? (
                <div className="space-y-3">
                  {customRules.map((rule, index) => (
                    <div key={index} className="flex items-start space-x-3 p-3 bg-white/5 rounded-lg">
                      {getCategoryIcon(rule.category)}
                      <div className="flex-1">
                        <p className="text-white text-sm">{rule.instruction}</p>
                        <span className="text-xs text-fg-2 capitalize">{rule.category}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6">
                  <BookOpen className="w-12 h-12 mx-auto mb-3 text-fg-3" />
                  <p className="text-fg-2">
                    {userRole === 'admin' 
                      ? 'No custom rules added yet. Create rules above to customize redlining behavior.'
                      : 'No redlining rules available. Contact your administrator to set up rules.'
                    }
                  </p>
                </div>
              )}
            </div>

            {/* Firm Details */}
            <div className="panel p-6">
              <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                <Building className="w-5 h-5 mr-2 text-metal-mid" />
                Firm details for the signature block
              </h2>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Firm name</label>
                  <input
                    type="text"
                    value={firmDetails.name}
                    onChange={(e) => updateFirmDetails('name', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Address</label>
                  <input
                    type="text"
                    value={firmDetails.address}
                    onChange={(e) => updateFirmDetails('address', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">City</label>
                  <input
                    type="text"
                    value={firmDetails.city}
                    onChange={(e) => updateFirmDetails('city', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">State</label>
                  <input
                    type="text"
                    value={firmDetails.state}
                    onChange={(e) => updateFirmDetails('state', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">ZIP code</label>
                  <input
                    type="text"
                    value={firmDetails.zipCode}
                    onChange={(e) => updateFirmDetails('zipCode', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Signer name</label>
                  <input
                    type="text"
                    value={firmDetails.signerName}
                    onChange={(e) => updateFirmDetails('signerName', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Title</label>
                  <input
                    type="text"
                    value={firmDetails.signerTitle}
                    onChange={(e) => updateFirmDetails('signerTitle', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Email</label>
                  <input
                    type="email"
                    value={firmDetails.email}
                    onChange={(e) => updateFirmDetails('email', e.target.value)}
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={firmDetails.phone}
                    onChange={(e) => updateFirmDetails('phone', e.target.value)}
                    className="field"
                  />
                </div>
              </div>
            </div>

            {/* Process Button */}
            <button
              onClick={startProcessing}
              disabled={!getCurrentUploadedFile() || isProcessing}
              className="btn-metal w-full"
            >
              {isProcessing ? (
                <>
                  <Loader className="w-5 h-5 animate-spin" />
                  <span>AI Processing...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Redline this NDA</span>
                </>
              )}
            </button>
          </div>

          {/* Right Column - Processing & Preview */}
          <div className="space-y-8">
            {/* Processing Status */}
            {isProcessing && (
              <div className="panel p-6">
                <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                  <Sparkles className="w-5 h-5 mr-2 text-metal-mid" />
                  Redlining your NDA
                </h2>
                
                <div className="space-y-4">
                  {processingSteps.map((step, index) => (
                    <div key={step.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <span className="text-white/90">{step.name}</span>
                          {index === currentStep && step.details && (
                            <p className="text-sm text-fg-2 mt-1">{step.details}</p>
                          )}
                        </div>
                        {index === currentStep ? (
                          <div className="flex items-center space-x-2">
                            <Sparkles className="w-4 h-4 text-metal-mid animate-pulse" />
                            <span className="text-xs text-metal-mid">Working</span>
                          </div>
                        ) : index < currentStep ? (
                          <CheckCircle className="w-4 h-4 text-ok" />
                        ) : (
                          <div className="w-4 h-4 border-2 border-line rounded-full" />
                        )}
                      </div>
                      
                      {index === currentStep && (
                        <div className="w-full bg-white/10 rounded-full h-2">
                          <div 
                            className="bg-gradient-to-r from-metal-floor to-metal-peak h-2 rounded-full transition-all duration-300"
                            style={{ width: `${Math.min(100, (Date.now() % 2000) / 20)}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Preview Section */}
            {showPreview && (
              <div className="panel p-6">
                <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                  <Eye className="w-5 h-5 mr-2 text-metal-mid" />
                  Redline ready
                </h2>
                
                
                {getCurrentProcessingResult() && (
                  <dl className="mb-6 text-[0.95rem]">
                    <div className="flex justify-between gap-4 border-b border-line py-2"><dt className="text-fg-2">Rules applied</dt><dd className="tabular-nums text-white">{getCurrentProcessingResult()?.rules_applied ?? '—'}</dd></div>
                    <div className="flex justify-between gap-4 border-b border-line py-2"><dt className="text-fg-2">Changes made</dt><dd className="tabular-nums text-white">{getCurrentProcessingResult()?.changes_made ?? '—'}</dd></div>
                    <div className="flex justify-between gap-4 border-b border-line py-2"><dt className="text-fg-2">Processing time</dt><dd className="tabular-nums text-white">{getCurrentProcessingResult()?.processing_time ?? '—'}</dd></div>
                  </dl>
                )}
                
                <button
                  onClick={downloadDocument}
                  disabled={!getCurrentUploadedDocument()?.output_path}
                  className="btn-metal sm w-full"
                >
                  <Download className="w-5 h-5" />
                  <span>
                    {getCurrentUploadedDocument()?.output_path 
                      ? 'Download the redline' 
                      : 'Run the review to get a download'
                    }
                  </span>
                </button>
              </div>
            )}

            {/* AI Capabilities */}
            <div className="panel p-6">
              <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                <Sparkles className="w-5 h-5 mr-2 text-metal-mid" />
                What the redline covers
              </h2>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  <Target className="w-4 h-4 text-metal-mid" />
                  <span className="text-white/90">Custom instruction processing</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Zap className="w-4 h-4 text-metal-mid" />
                  <span className="text-white/90">AI-powered document analysis</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Building className="w-4 h-4 text-metal-mid" />
                  <span className="text-white/90">Automatic firm detail insertion</span>
                </div>
                <div className="flex items-center space-x-3">
                  <PenTool className="w-4 h-4 text-metal-mid" />
                  <span className="text-white/90">Signature block completion</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Calendar className="w-4 h-4 text-metal-mid" />
                  <span className="text-white/90">Term duration optimization</span>
                </div>
                <div className="flex items-center space-x-3">
                  <Lock className="w-4 h-4 text-metal-mid" />
                  <span className="text-white/90">Liability clause analysis</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Admin Rule Creation Modal */}
      {showAdminRuleModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div ref={adminRuleModalRef} className="bg-ink-panel rounded-xl p-6 w-full max-w-md mx-4 border border-line">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">New rule</h3>
              <button
                onClick={() => setShowAdminRuleModal(false)}
                className="text-fg-2 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-fg-2 mb-2">
                  Rule name
                </label>
                <input
                  type="text"
                  value={adminRuleName}
                  onChange={(e) => setAdminRuleName(e.target.value)}
                  placeholder="Enter rule name..."
                  className="field"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-fg-2 mb-2">
                  Category
                </label>
                <select
                  value={adminRuleCategory}
                  onChange={(e) => setAdminRuleCategory(e.target.value)}
                  className="w-full bg-ink-well border border-line rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-white/15"
                >
                  <option value="term">Term</option>
                  <option value="parties">Parties</option>
                  <option value="firm">Firm Details</option>
                  <option value="signature">Signature</option>
                  <option value="other">Other</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-fg-2 mb-2">
                  Redlining Instruction
                </label>
                <textarea
                  value={adminRuleInstruction}
                  onChange={(e) => setAdminRuleInstruction(e.target.value)}
                  placeholder="Enter detailed redlining instruction..."
                  rows={3}
                  className="field resize-none"
                />
              </div>
              
              <div className="flex space-x-3 pt-2">
                <button
                  onClick={() => setShowAdminRuleModal(false)}
                  className="btn-quiet sm flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={createAdminRule}
                  className="btn-metal sm flex-1"
                >
                  Create Rule
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div ref={addUserModalRef} className="bg-ink-panel rounded-xl p-6 w-full max-w-md mx-4 border border-line">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Add a user</h3>
              <button
                onClick={() => setShowAddUserModal(false)}
                className="text-fg-2 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-fg-2 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={newUserData.username}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="Enter username..."
                  className="field"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-fg-2 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  value={newUserData.email}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="Enter email..."
                  className="field"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-fg-2 mb-2">
                  Role
                </label>
                <select
                  value={newUserData.role}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full bg-ink-well border border-line rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-white/15"
                >
                  <option value="USER">Reviewer</option>
                  <option value="ADMIN">Administrator</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-fg-2 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={newUserData.password}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Enter password..."
                  className="field"
                />
              </div>
              
              <div className="flex space-x-3 pt-2">
                <button
                  onClick={() => setShowAddUserModal(false)}
                  className="btn-quiet sm flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={addNewUser}
                  className="btn-metal sm flex-1"
                >
                  Create User
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* System Health Modal */}
      {/* This modal is removed as per the edit hint */}
    </div>
  )
}


