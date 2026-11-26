'use client';

import { AppHeader, PageIntro } from '../../components/app-header'
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
      setError('Run the review to get a download');
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

  const getCategoryIcon = (_category: string) => (
    <span aria-hidden="true" className="mt-[0.7em] block h-[2px] w-3 shrink-0 rounded bg-redline" />
  );

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-black text-white/90 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-metal-mid border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-xl text-fg-2">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect if not authenticated or if admin
  if (!isAuthenticated || user?.role === 'ADMIN') {
    return null;
  }

  return (
    <div className="min-h-screen bg-black text-white/90">
      {/* Header */}
      <AppHeader section="Review workspace" role="USER" onSignOut={handleLogout}></AppHeader>

      <div className="mx-auto max-w-[1400px] px-5 py-12 md:px-8 md:py-16">
        <PageIntro title="Review an NDA">Upload the counterparty’s .docx, choose the rules your admin set up, then review each proposed change.</PageIntro>

        {/* Error Display */}
        {error && (
          <div className="mb-8 bg-redline-wash border border-redline/50 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <div className="w-5 h-5 bg-red-500 rounded-full" />
              <span className="text-redline-text">{error}</span>
            </div>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="mb-8 bg-ok-wash border border-ok/40 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <div className="w-5 h-5 bg-green-500 rounded-full" />
              <span className="text-ok">{success}</span>
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
              
              {!uploadedFile ? (
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
                      <p className="font-medium text-white">{uploadedFile.name}</p>
                      <p className="text-sm text-fg-2">
                        {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <button
                      onClick={() => setUploadedFile(null)}
                      className="text-fg-2 hover:text-white transition-colors"
                    >
                      ×
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Rules from your admin */}
            <div className="panel p-6">
              <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                <Shield className="w-5 h-5 mr-2 text-metal-mid" />
                Rules from your admin
              </h2>
              
              <div className="space-y-4">
                {customRules.length > 0 ? (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-fg-2">Active rules</h3>
                    {customRules.map((rule, index) => (
                      <div key={index} className="flex items-center space-x-3 bg-ink-panel rounded-lg p-3">
                        {getCategoryIcon(rule.category)}
                        <div>
                          {rule.name && (
                            <div className="text-sm font-medium text-white">{rule.name}</div>
                          )}
                          <span className="text-sm text-white/90">{rule.instruction}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Shield className="w-12 h-12 mx-auto mb-4 text-fg-3" />
                    <p className="text-fg-2">No rules yet</p>
                    <p className="text-sm text-fg-3 mt-2">Ask your admin to add the rules your firm uses.</p>
                    <p className="text-xs text-fg-3 mt-1">Rules you add will be listed here.</p>
                  </div>
                )}
              </div>
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
                    placeholder="Halden Capital LLC"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Address</label>
                  <input
                    type="text"
                    value={firmDetails.address}
                    onChange={(e) => updateFirmDetails('address', e.target.value)}
                    placeholder="Enter street address"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">City</label>
                  <input
                    type="text"
                    value={firmDetails.city}
                    onChange={(e) => updateFirmDetails('city', e.target.value)}
                    placeholder="Enter city"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">State</label>
                  <input
                    type="text"
                    value={firmDetails.state}
                    onChange={(e) => updateFirmDetails('state', e.target.value)}
                    placeholder="Enter state (e.g., NY)"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">ZIP code</label>
                  <input
                    type="text"
                    value={firmDetails.zipCode}
                    onChange={(e) => updateFirmDetails('zipCode', e.target.value)}
                    placeholder="Enter ZIP code"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Signer name</label>
                  <input
                    type="text"
                    value={firmDetails.signerName}
                    onChange={(e) => updateFirmDetails('signerName', e.target.value)}
                    placeholder="Enter signer's full name"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Title</label>
                  <input
                    type="text"
                    value={firmDetails.signerTitle}
                    onChange={(e) => updateFirmDetails('signerTitle', e.target.value)}
                    placeholder="Enter signer's title"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Email</label>
                  <input
                    type="email"
                    value={firmDetails.email}
                    onChange={(e) => updateFirmDetails('email', e.target.value)}
                    placeholder="Enter email address"
                    className="field"
                  />
                </div>
                <div>
                  <label className="block text-sm text-fg-2 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={firmDetails.phone}
                    onChange={(e) => updateFirmDetails('phone', e.target.value)}
                    placeholder="Enter phone number"
                    className="field"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Processing & Results */}
          <div className="space-y-8">
            {/* Processing Controls */}
            <div className="panel p-6">
              <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                <Zap className="w-5 h-5 mr-2 text-metal-mid" />
                Run the review
              </h2>
              
              <div className="space-y-4">
                <button
                  onClick={startProcessing}
                  disabled={!uploadedFile || isProcessing}
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
                
                {uploadedDocument && (
                  <button
                    onClick={downloadDocument}
                    className="btn-metal sm w-full"
                  >
                    <Download className="w-5 h-5 inline mr-2" />
                    Download Processed Document
                  </button>
                )}
              </div>
            </div>

            {/* Processing Steps */}
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


                {processingResult && (
                  <dl className="mb-6 text-[0.95rem]">
                    <div className="flex justify-between gap-4 border-b border-line py-2"><dt className="text-fg-2">Rules applied</dt><dd className="tabular-nums text-white">{processingResult.rules_applied}</dd></div>
                    <div className="flex justify-between gap-4 border-b border-line py-2"><dt className="text-fg-2">Changes made</dt><dd className="tabular-nums text-white">{processingResult.changes_made}</dd></div>
                    <div className="flex justify-between gap-4 border-b border-line py-2"><dt className="text-fg-2">Processing time</dt><dd className="tabular-nums text-white">{processingResult.processing_time}</dd></div>
                  </dl>
                )}

                <button
                  onClick={downloadDocument}
                  disabled={!uploadedDocument?.output_path}
                  className="btn-metal sm w-full"
                >
                  <Download className="w-5 h-5" />
                  <span>
                    {uploadedDocument?.output_path
                      ? 'Download the redline'
                      : 'Run the review to get a download'
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
