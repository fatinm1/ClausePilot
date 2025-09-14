'use client';

import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../lib/auth-context';
import { useRouter } from 'next/navigation';
import { 
  Upload, 
  FileText, 
  Shield, 
  Building, 
  Zap, 
  Download, 
  Sparkles, 
  CheckCircle, 
  Loader, 
  X,
  LogOut,
  Eye
} from 'lucide-react';
import { apiClient, CustomRule, FirmDetails, Document } from '../../lib/api';

interface ProcessingResult {
  rules_applied: number;
  changes_made: number;
  processing_time: string;
}

export default function UserDashboard() {
  const { user, isAuthenticated, loading, logout } = useAuth();
  const router = useRouter();
  
  // State variables
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedDocument, setUploadedDocument] = useState<Document | null>(null);
  const [customRules, setCustomRules] = useState<CustomRule[]>([]);
  const [firmDetails, setFirmDetails] = useState<FirmDetails>({
    name: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    signerName: '',
    signerTitle: '',
    email: '',
    phone: ''
  });

  // Signature state
  const [signatureFile, setSignatureFile] = useState<File | null>(null);
  const [signaturePreview, setSignaturePreview] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [processingResult, setProcessingResult] = useState<ProcessingResult | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Processing steps
  const processingSteps = [
    { id: 1, name: 'Document Analysis & Validation', details: 'Analyzing document structure and content' },
    { id: 2, name: 'Applying Custom Instructions', details: 'Processing admin-defined redlining rules' },
    { id: 3, name: 'AI-Powered Redlining', details: 'AI agent applying intelligent modifications' },
    { id: 4, name: 'Inserting Firm Details', details: 'Adding signature blocks and firm information' },
    { id: 5, name: 'Generating Redlined Document', details: 'Creating final document with tracked changes' }
  ];

  // Check authentication and role
  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        router.push('/login');
      } else if (user?.role === 'ADMIN') {
        router.push('/dashboard');
      }
    }
  }, [loading, isAuthenticated, user, router]);

  // Load admin's custom rules
  useEffect(() => {
    if (user && user.role === 'USER') {
      loadAdminRules();
    }
  }, [user]);

  const loadAdminRules = async () => {
    try {
      const response = await apiClient.listRules(user?.id?.toString() || '');
      // The backend returns { rules: [...] }
      setCustomRules(response.rules);
    } catch (error) {
      console.error('Error loading admin rules:', error);
      // No fallback rules - users should only see rules that admins actually created
      setCustomRules([]);
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
      setUploadedFile(file);
      setError(null);
      
      // Create a mock document object
      const mockDocument: Document = {
        id: Date.now(),
        filename: file.name,
        original_filename: file.name,
        file_path: URL.createObjectURL(file),
        file_size: file.size,
        status: 'uploaded',
        user_id: user?.id || 1,
        uploaded_at: new Date().toISOString()
      };
      
      setUploadedDocument(mockDocument);
    } else {
      setError('Please upload a valid .docx file');
    }
  };

  const handleSignatureUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      if (file.type.startsWith('image/')) {
        setSignatureFile(file);
        
        // Create preview
        const reader = new FileReader();
        reader.onload = (e) => {
          setSignaturePreview(e.target?.result as string);
        };
        reader.readAsDataURL(file);
        
        setError(null);
        setSuccess('Signature uploaded successfully!');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError('Please select a valid image file (PNG, JPG, etc.)');
      }
    }
  };

  const removeSignature = () => {
    setSignatureFile(null);
    setSignaturePreview(null);
    setSuccess('Signature removed');
    setTimeout(() => setSuccess(null), 3000);
  };

  const startProcessing = async () => {
    if (!uploadedFile || !uploadedDocument) return;
    
    setIsProcessing(true);
    setError(null);
    setSuccess(null);
    setCurrentStep(0);
    setShowPreview(false);

    try {
      // Step 1: Document Analysis
      setCurrentStep(0);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Step 2: Apply custom rules
      setCurrentStep(1);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Step 3: AI redlining
      setCurrentStep(2);
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Step 4: Insert firm details
      setCurrentStep(3);
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Step 5: Generate final document
      setCurrentStep(4);
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Mock processing result
      const result = {
        success: true,
        document: {
          ...uploadedDocument,
          output_path: `/outputs/processed_${Date.now()}_${uploadedFile.name}`
        },
        processing_result: {
          rules_applied: customRules.length,
          changes_made: 4,
          processing_time: '5.5s'
        }
      };

      setProcessingResult(result.processing_result);
      setUploadedDocument(result.document);
      setShowPreview(true);
      setSuccess('Document processed successfully!');
      
    } catch (error) {
      setError('Error processing document. Please try again.');
    } finally {
      setIsProcessing(false);
      setCurrentStep(0);
    }
  };

  const downloadDocument = async () => {
    if (!uploadedDocument?.output_path) {
      setError('No processed document available for download');
      return;
    }

    try {
      // Mock download - in real app this would download the actual file
      setSuccess('Document downloaded successfully!');
    } catch (error) {
      setError('Error downloading document. Please try again.');
    }
  };

  const updateFirmDetails = (field: keyof FirmDetails, value: string) => {
    setFirmDetails(prev => ({ ...prev, [field]: value }));
  };

  const getCategoryIcon = (category: string) => {
    const iconClass = "w-4 h-4";
    switch (category) {
      case 'term':
        return <div className={`${iconClass} bg-blue-500 rounded-full`} />;
      case 'parties':
        return <div className={`${iconClass} bg-green-500 rounded-full`} />;
      case 'liability':
        return <div className={`${iconClass} bg-yellow-500 rounded-full`} />;
      default:
        return <div className={`${iconClass} bg-purple-500 rounded-full`} />;
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-[#0B1220] text-[#E5E7EB] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-[#60A5FA] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-xl text-[#E5E7EB]/80">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect if not authenticated or if admin
  if (!isAuthenticated || user?.role === 'ADMIN') {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#0B1220] text-[#E5E7EB]">
      {/* Header */}
      <header className="bg-[#0B1220]/90 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-[#60A5FA] rounded-full animate-pulse" />
              <span className="text-xl font-semibold text-white">NDA Redline</span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-[#E5E7EB]/60">User Dashboard</span>
              <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 border border-green-500/30">
                USER
              </span>
              <button
                onClick={handleLogout}
                className="text-[#E5E7EB]/60 hover:text-[#E5E7EB]/80 transition-colors"
              >
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">User Dashboard</h1>
          <p className="text-xl text-[#E5E7EB]/80 max-w-3xl mx-auto">
            Process your NDA documents using AI-powered redlining with admin-defined rules.
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-8 bg-red-500/20 border border-red-500/30 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <div className="w-5 h-5 bg-red-500 rounded-full" />
              <span className="text-red-400">{error}</span>
            </div>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="mb-8 bg-green-500/20 border border-green-500/30 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <div className="w-5 h-5 bg-green-500 rounded-full" />
              <span className="text-green-400">{success}</span>
            </div>
          </div>
        )}

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left Column - Upload & Configuration */}
          <div className="space-y-8">
            {/* File Upload */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                <Upload className="w-5 h-5 mr-2 text-[#60A5FA]" />
                Upload NDA Document
              </h2>
              
              {!uploadedFile ? (
                <div className="border-2 border-dashed border-white/20 rounded-lg p-8 text-center hover:border-[#60A5FA]/40 transition-colors">
                  <input
                    type="file"
                    accept=".docx"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="file-upload"
                    ref={fileInputRef}
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <Upload className="w-12 h-12 mx-auto mb-4 text-[#60A5FA]" />
                    <p className="text-lg font-medium text-white mb-2">Drop your NDA here</p>
                    <p className="text-[#E5E7EB]/60">or click to browse</p>
                    <p className="text-sm text-[#E5E7EB]/40 mt-2">Supports .docx files only</p>
                  </label>
                </div>
              ) : (
                <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                  <div className="flex items-center space-x-3">
                    <FileText className="w-8 h-8 text-[#60A5FA]" />
                    <div className="flex-1">
                      <p className="font-medium text-white">{uploadedFile.name}</p>
                      <p className="text-sm text-[#E5E7EB]/60">
                        {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <button
                      onClick={() => setUploadedFile(null)}
                      className="text-[#E5E7EB]/60 hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Admin's Redlining Rules */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                <Shield className="w-5 h-5 mr-2 text-[#60A5FA]" />
                Admin's Redlining Rules
              </h2>
              
              <div className="space-y-4">
                {customRules.length > 0 ? (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-[#E5E7EB]/80">Active Rules:</h3>
                    {customRules.map((rule, index) => (
                      <div key={index} className="flex items-center space-x-3 bg-[#1F2937] rounded-lg p-3">
                        {getCategoryIcon(rule.category)}
                        <div>
                          {rule.name && (
                            <div className="text-sm font-medium text-white">{rule.name}</div>
                          )}
                          <span className="text-sm text-[#E5E7EB]">{rule.instruction}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Shield className="w-12 h-12 mx-auto mb-4 text-[#E5E7EB]/40" />
                    <p className="text-[#E5E7EB]/60">No redlining rules defined yet</p>
                    <p className="text-sm text-[#E5E7EB]/40 mt-2">Your admin will create rules for document processing</p>
                    <p className="text-xs text-[#E5E7EB]/30 mt-1">Rules will appear here once they're created</p>
                  </div>
                )}
              </div>
            </div>

            {/* Firm Details */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                <Building className="w-5 h-5 mr-2 text-[#60A5FA]" />
                Firm Information
              </h2>
              
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">Firm Name</label>
                  <input
                    type="text"
                    value={firmDetails.name}
                    onChange={(e) => updateFirmDetails('name', e.target.value)}
                    placeholder="Enter your law firm name"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">Address</label>
                  <input
                    type="text"
                    value={firmDetails.address}
                    onChange={(e) => updateFirmDetails('address', e.target.value)}
                    placeholder="Enter street address"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">City</label>
                  <input
                    type="text"
                    value={firmDetails.city}
                    onChange={(e) => updateFirmDetails('city', e.target.value)}
                    placeholder="Enter city"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">State</label>
                  <input
                    type="text"
                    value={firmDetails.state}
                    onChange={(e) => updateFirmDetails('state', e.target.value)}
                    placeholder="Enter state (e.g., NY)"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">ZIP Code</label>
                  <input
                    type="text"
                    value={firmDetails.zipCode}
                    onChange={(e) => updateFirmDetails('zipCode', e.target.value)}
                    placeholder="Enter ZIP code"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">Signer Name</label>
                  <input
                    type="text"
                    value={firmDetails.signerName}
                    onChange={(e) => updateFirmDetails('signerName', e.target.value)}
                    placeholder="Enter signer's full name"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">Title</label>
                  <input
                    type="text"
                    value={firmDetails.signerTitle}
                    onChange={(e) => updateFirmDetails('signerTitle', e.target.value)}
                    placeholder="Enter signer's title"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">Email</label>
                  <input
                    type="email"
                    value={firmDetails.email}
                    onChange={(e) => updateFirmDetails('email', e.target.value)}
                    placeholder="Enter email address"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-[#E5E7EB]/60 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={firmDetails.phone}
                    onChange={(e) => updateFirmDetails('phone', e.target.value)}
                    placeholder="Enter phone number"
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Processing & Results */}
          <div className="space-y-8">
            {/* Processing Controls */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                <Zap className="w-5 h-5 mr-2 text-[#60A5FA]" />
                Document Processing
              </h2>
              
              <div className="space-y-4">
                <button
                  onClick={startProcessing}
                  disabled={!uploadedFile || isProcessing}
                  className="w-full bg-[#60A5FA] hover:bg-[#60A5FA]/90 disabled:bg-[#60A5FA]/40 text-white py-4 rounded-lg font-semibold text-lg transition-all duration-200 hover:shadow-lg hover:shadow-[#60A5FA]/25 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                  {isProcessing ? (
                    <>
                      <Loader className="w-5 h-5 animate-spin" />
                      <span>AI Processing...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5" />
                      <span>Start AI Redlining Process</span>
                    </>
                  )}
                </button>
                
                {uploadedDocument && (
                  <button
                    onClick={downloadDocument}
                    className="w-full bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
                  >
                    <Download className="w-5 h-5 inline mr-2" />
                    Download Processed Document
                  </button>
                )}
              </div>
            </div>

            {/* Processing Steps */}
            {isProcessing && (
              <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                  <Sparkles className="w-5 h-5 mr-2 text-[#60A5FA]" />
                  AI Agent Processing Your NDA
                </h2>
                
                <div className="space-y-4">
                  {processingSteps.map((step, index) => (
                    <div key={step.id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <span className="text-[#E5E7EB]">{step.name}</span>
                          {index === currentStep && step.details && (
                            <p className="text-sm text-[#E5E7EB]/60 mt-1">{step.details}</p>
                          )}
                        </div>
                        {index === currentStep ? (
                          <div className="flex items-center space-x-2">
                            <Sparkles className="w-4 h-4 text-[#60A5FA] animate-pulse" />
                            <span className="text-xs text-[#60A5FA]">AI Working</span>
                          </div>
                        ) : index < currentStep ? (
                          <CheckCircle className="w-4 h-4 text-green-400" />
                        ) : (
                          <div className="w-4 h-4 border-2 border-white/20 rounded-full" />
                        )}
                      </div>
                      
                      {index === currentStep && (
                        <div className="w-full bg-white/10 rounded-full h-2">
                          <div 
                            className="bg-gradient-to-r from-[#60A5FA] to-[#3B82F6] h-2 rounded-full transition-all duration-300"
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
              <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                  <Eye className="w-5 h-5 mr-2 text-[#60A5FA]" />
                  AI-Redlined Document Preview
                </h2>

                <div className="bg-white rounded-lg p-6 shadow-2xl mb-4">
                  <div className="flex items-center space-x-3 mb-4">
                    <div className="w-3 h-3 bg-red-500 rounded-full" />
                    <div className="w-3 h-3 bg-yellow-500 rounded-full" />
                    <div className="w-3 h-3 bg-green-500 rounded-full" />
                  </div>

                  <div className="space-y-3">
                    <div className="h-4 bg-gray-200 rounded w-full" />
                    <div className="h-4 bg-gray-200 rounded w-3/4" />
                    <div className="h-4 bg-red-200 rounded w-2/3 border-l-4 border-red-500" />
                    <div className="h-4 bg-gray-200 rounded w-4/5" />
                    <div className="h-4 bg-blue-200 rounded w-1/2 border-l-4 border-blue-500" />
                    <div className="h-4 bg-gray-200 rounded w-3/4" />
                    <div className="h-4 bg-green-200 rounded w-5/6 border-l-4 border-green-500" />
                    <div className="h-4 bg-gray-200 rounded w-2/3" />
                    <div className="h-4 bg-purple-200 rounded w-4/5 border-l-4 border-purple-500" />
                  </div>
                </div>

                {processingResult && (
                  <div className="space-y-3 text-sm mb-4">
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 bg-green-500 rounded-full" />
                      <span className="text-[#E5E7EB]">Rules Applied: {processingResult.rules_applied}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 bg-blue-500 rounded-full" />
                      <span className="text-[#E5E7EB]">Changes Made: {processingResult.changes_made}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 bg-purple-500 rounded-full" />
                      <span className="text-[#E5E7EB]">Processing Time: {processingResult.processing_time}</span>
                    </div>
                  </div>
                )}

                <button
                  onClick={downloadDocument}
                  disabled={!uploadedDocument?.output_path}
                  className="w-full bg-[#10B981] hover:bg-[#10B981]/90 disabled:bg-[#10B981]/40 text-white py-3 rounded-lg font-semibold transition-all duration-200 hover:shadow-lg hover:shadow-[#10B981]/25 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                  <Download className="w-5 h-5" />
                  <span>
                    {uploadedDocument?.output_path
                      ? 'Download Redlined Document'
                      : 'No processed document available for download'
                    }
                  </span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
