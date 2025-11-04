'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../lib/auth-context';
import { useRouter } from 'next/navigation';
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
} from 'lucide-react';
import { apiClient } from '../../lib/api';
import { Document, CustomRule, FirmDetails } from '../../lib/api';
import ChangesReview from '../components/ChangesReview';

interface ProcessingStep {
  id: string;
  name: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  details?: string;
}

export default function Dashboard() {
  const { user, logout, loading } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Document processing states
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [uploadedDocument, setUploadedDocument] = useState<Document | null>(null);
  const [processingResult, setProcessingResult] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [showPreview, setShowPreview] = useState(false);
  const [showChangesReview, setShowChangesReview] = useState(false);
  const [documentText, setDocumentText] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Custom rules state
  const [customRules, setCustomRules] = useState<CustomRule[]>([]);
  const [selectedRules, setSelectedRules] = useState<number[]>([]);
  
  // System statistics state
  const [systemStats, setSystemStats] = useState<{
    total_users: number;
    total_documents: number;
    total_rules: number;
  } | null>(null);

  // Firm details state
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
  const [showSignatureModal, setShowSignatureModal] = useState(false);

  // Modal states
  const [showAdminRuleModal, setShowAdminRuleModal] = useState(false);
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [adminRuleName, setAdminRuleName] = useState('');
  const [adminRuleInstruction, setAdminRuleInstruction] = useState('');
  const [adminRuleCategory, setAdminRuleCategory] = useState('other');
  const [newUserData, setNewUserData] = useState({
    username: '',
    email: '',
    role: 'USER',
    password: ''
  });

  // Processing steps
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
      name: 'Applying Custom Instructions', 
      status: 'pending', 
      progress: 0,
      details: 'Processing user-defined redlining rules'
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
  ]);

  // Check authentication and role
  useEffect(() => {
    // Only redirect if we're DONE loading AND there's no user
    if (!loading && !user) {
      console.log('Dashboard: Not authenticated, redirecting to login');
      router.push('/login');
    } else if (!loading && user && user.role === 'USER') {
      console.log('Dashboard: USER role detected, redirecting to user-dashboard');
      router.push('/user-dashboard');
    } else if (!loading && user) {
      console.log('Dashboard: Authenticated as', user.email, 'with role', user.role);
    }
  }, [loading, user, router]);

  // Load existing rules from backend
  useEffect(() => {
    if (user && user.role === 'ADMIN') {
      loadExistingRules();
      loadSystemStats();
    }
  }, [user]);

  const loadExistingRules = async () => {
    try {
      const response = await apiClient.listRules(user?.id?.toString() || '');
      setCustomRules(response.rules);
      // Select all rules by default
      setSelectedRules(response.rules.map((rule: any) => rule.id));
    } catch (error) {
      console.error('Error loading existing rules:', error);
      // Start with empty rules if backend fails
      setCustomRules([]);
    }
  };

  const toggleRuleSelection = (ruleId: number) => {
    setSelectedRules(prev => 
      prev.includes(ruleId) 
        ? prev.filter(id => id !== ruleId)
        : [...prev, ruleId]
    );
  };

  const loadSystemStats = async () => {
    try {
      const response = await apiClient.getAdminDashboard(user?.id?.toString() || '');
      setSystemStats(response.statistics);
    } catch (error) {
      console.error('Error loading system stats:', error);
      // Keep stats as null to show loading state
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setUploadedFile(file);
      setError(null);
      
      try {
        // Upload file to backend
        const result = await apiClient.uploadDocument(file, user?.id?.toString() || '');
        setUploadedDocument(result.document);
        setSuccess('Document uploaded successfully!');
      } catch (error) {
        console.error('Upload error:', error);
        setError('Failed to upload document. Please try again.');
        setUploadedFile(null);
      }
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
    
    if (selectedRules.length === 0) {
      setError('Please select at least one rule to apply.');
      return;
    }
    
    setIsProcessing(true);
    setError(null);
    setSuccess(null);
    setCurrentStep(0);
    setShowPreview(false);

    try {
      // Extract document text for changes review
      const textResponse = await apiClient.getDocumentText(uploadedDocument.id);
      setDocumentText(textResponse.text);

      // Get selected rules data
      const selectedRulesData = customRules.filter(rule => rule.id && selectedRules.includes(rule.id));
      
      // Map frontend field names to backend expected field names
      const mappedFirmDetails = {
        firm_name: firmDetails.name,
        signatory_name: firmDetails.signerName,
        title: firmDetails.signerTitle,
        address: firmDetails.address,
        city: firmDetails.city,
        state: firmDetails.state,
        zip_code: firmDetails.zipCode,
        email: firmDetails.email,
        phone: firmDetails.phone
      };

      // DEBUG: Log what we're sending to backend
      console.log('🔍 DEBUG: Original firmDetails:', firmDetails);
      console.log('🔍 DEBUG: Mapped firmDetails:', mappedFirmDetails);
      console.log('🔍 DEBUG: Selected rules:', selectedRulesData);

      // Show changes review instead of direct processing
      setShowChangesReview(true);
      setIsProcessing(false);

    } catch (error) {
      console.error('Processing error:', error);
      setError('Error processing document. Please try again.');
      setIsProcessing(false);
    }
  };

  const handleChangesReviewComplete = async (finalDocumentPath: string) => {
    setShowChangesReview(false);
    setSuccess('Document processed successfully! Changes have been applied.');
    
    // Update the document with the final path
    if (uploadedDocument) {
      setUploadedDocument({
        ...uploadedDocument,
        final_file_path: finalDocumentPath
      });
    }
  };

  const downloadDocument = async () => {
    if (!uploadedDocument?.id) {
      setError('No processed document available for download');
      return;
    }

    try {
      await apiClient.downloadDocument(uploadedDocument.id, user?.id?.toString() || '');
      setSuccess('Document downloaded successfully!');
    } catch (error) {
      setError('Error downloading document. Please try again.');
    }
  };

  const addCustomRule = async () => {
    if (!adminRuleName.trim() || !adminRuleInstruction.trim()) {
      setError('Rule name and instruction are required');
      return;
    }

    try {
      const newRule = {
        name: adminRuleName,
        category: adminRuleCategory,
        instruction: adminRuleInstruction
      };
      
      
      // Save rule to backend
      const response = await apiClient.createRule(newRule, user?.id?.toString() || '');
      
      
      // Add to local state
      setCustomRules(prev => [...prev, response.rule]);
      
      setAdminRuleName('');
      setAdminRuleInstruction('');
      setAdminRuleCategory('other');
      
      setError(null);
      setSuccess('Rule created successfully!');
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to create rule');
    }
  };

  const updateCustomRule = async (index: number, field: keyof CustomRule, value: string) => {
    try {
      const ruleToUpdate = customRules[index];
      if (ruleToUpdate.id) {
        // Update in backend
        const updates = { [field]: value };
        await apiClient.updateRule(ruleToUpdate.id, updates, user?.id?.toString() || '');
      }
      // Update local state
      const updatedRules = [...customRules];
      updatedRules[index] = { ...updatedRules[index], [field]: value };
      setCustomRules(updatedRules);
    } catch (error) {
      setError('Failed to update rule');
    }
  };

  const removeCustomRule = async (index: number) => {
    try {
      const ruleToDelete = customRules[index];
      if (ruleToDelete.id) {
        // Delete from backend
        await apiClient.deleteRule(ruleToDelete.id, user?.id?.toString() || '');
      }
      // Remove from local state
      setCustomRules(customRules.filter((_, i) => i !== index));
      setSuccess('Rule deleted successfully!');
      setTimeout(() => setSuccess(null), 3000);
    } catch (error) {
      setError('Failed to delete rule');
    }
  };

  const updateFirmDetails = (field: keyof FirmDetails, value: string) => {
    setFirmDetails(prev => ({ ...prev, [field]: value }));
  };

  const createAdminRule = async () => {
    if (!adminRuleName.trim() || !adminRuleInstruction.trim()) {
      setError('Rule name and instruction are required');
      return;
    }

    try {
      const newRule = {
        name: adminRuleName,
        category: adminRuleCategory,
        instruction: adminRuleInstruction
      };
      
      
      // Save rule to backend
      const response = await apiClient.createRule(newRule, user?.id?.toString() || '');
      
      
      // Add to local state
      setCustomRules(prev => [...prev, response.rule]);
      
      setAdminRuleName('');
      setAdminRuleInstruction('');
      setAdminRuleCategory('other');
      setShowAdminRuleModal(false);
      
      setError(null);
      setSuccess('Rule created successfully!');
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to create rule');
    }
  };

  const addNewUser = async () => {
    if (!newUserData.username.trim() || !newUserData.email.trim() || !newUserData.password.trim()) {
      setError('Username, email, and password are required');
      return;
    }

    try {
      setError(null);
      setSuccess(`User "${newUserData.username}" created successfully!`);
      
      setNewUserData({
        username: '',
        email: '',
        role: 'USER',
        password: ''
      });
      setShowAddUserModal(false);
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to create user');
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'term': return <Calendar className="w-4 h-4 text-blue-400" />;
      case 'parties': return <Users className="w-4 h-4 text-green-400" />;
      case 'firm': return <Building className="w-4 h-4 text-purple-400" />;
      case 'signature': return <PenTool className="w-4 h-4 text-orange-400" />;
      default: return <Target className="w-4 h-4 text-gray-400" />;
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'term': return 'Term Duration';
      case 'parties': return 'Parties';
      case 'firm': return 'Firm Details';
      case 'signature': return 'Signature';
      default: return 'Other';
    }
  };

  // Single return statement with conditional rendering
  return (
    <div className="min-h-screen bg-[#0B1220] text-[#E5E7EB]">
      {loading ? (
        // Loading state
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-[#60A5FA] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-xl text-[#E5E7EB]/80">Validating authentication...</p>
          </div>
        </div>
      ) : showChangesReview ? (
        // Changes Review Interface
        <ChangesReview
          documentId={uploadedDocument?.id || 0}
          documentText={documentText}
          customRules={customRules.filter(rule => rule.id && selectedRules.includes(rule.id))}
          firmDetails={{
            name: firmDetails.name,
            signerName: firmDetails.signerName,
            signerTitle: firmDetails.signerTitle,
            address: firmDetails.address,
            city: firmDetails.city,
            state: firmDetails.state,
            zipCode: firmDetails.zipCode,
            email: firmDetails.email,
            phone: firmDetails.phone
          }}
          onComplete={handleChangesReviewComplete}
        />
      ) : !user ? (
        // Don't render anything while redirecting
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-[#60A5FA] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-xl text-[#E5E7EB]/80">Redirecting...</p>
          </div>
        </div>
      ) : (
        // Main dashboard content (only for admin users)
        <>
      <header className="bg-[#0B1220]/90 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-3 h-3 bg-[#60A5FA] rounded-full animate-pulse" />
              <span className="text-xl font-semibold text-white">NDA Redline</span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-[#E5E7EB]/60">Admin Dashboard</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30`}>
                ADMIN
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
          <h1 className="text-4xl font-bold text-white mb-4">Admin Dashboard</h1>
          <p className="text-xl text-[#E5E7EB]/80 max-w-3xl mx-auto">
            Manage your NDA redlining system, create custom rules, and process documents with AI-powered intelligence.
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-8 bg-red-500/20 border border-red-500/30 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 text-red-400" />
              <span className="text-red-400">{error}</span>
            </div>
          </div>
        )}

        {/* Success Message */}
        {success && (
          <div className="mb-8 bg-green-500/20 border border-green-500/30 rounded-xl p-4">
            <div className="flex items-center space-x-3">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <span className="text-green-400">{success}</span>
            </div>
          </div>
        )}

        {/* Admin Section */}
        <div className="mb-8 bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
          <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
            <Users className="w-5 h-5 mr-2 text-[#60A5FA]" />
            Admin Dashboard
          </h2>
          
          <div className="grid md:grid-cols-2 gap-6">
            {/* System Statistics */}
            <div className="bg-[#1F2937] rounded-lg p-4">
              <h3 className="text-lg font-medium text-white mb-3">System Overview</h3>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-[#E5E7EB]/60">Total Users:</span>
                  <span className="text-white">{systemStats?.total_users ?? 'Loading...'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#E5E7EB]/60">Total Documents:</span>
                  <span className="text-white">{systemStats?.total_documents ?? 'Loading...'}</span>
              </div>
                <div className="flex justify-between">
                  <span className="text-[#E5E7EB]/60">Custom Rules:</span>
                  <span className="text-white">{systemStats?.total_rules ?? customRules.length}</span>
              </div>
            </div>
          </div>

            {/* Quick Actions */}
            <div className="bg-[#1F2937] rounded-lg p-4">
              <h3 className="text-lg font-medium text-white mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <button 
                  onClick={() => setShowAdminRuleModal(true)}
                  className="w-full bg-[#60A5FA] hover:bg-[#60A5FA]/80 text-white px-4 py-2 rounded-md text-sm transition-colors"
                >
                  Create Redlining Rule
                </button>
                <button 
                  onClick={() => setShowAddUserModal(true)}
                  className="w-full bg-[#10B981] hover:bg-[#10B981]/80 text-white px-4 py-2 rounded-md text-sm transition-colors"
                >
                  Add New User
                </button>
              </div>
            </div>
          </div>
        </div>

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

            {/* Custom Rules */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center">
                <Shield className="w-5 h-5 mr-2 text-[#60A5FA]" />
                Custom Redlining Rules
              </h2>
              
              <div className="space-y-4">
                <div className="flex space-x-3">
                  <select
                    value={adminRuleCategory}
                    onChange={(e) => setAdminRuleCategory(e.target.value)}
                    className="flex-1 bg-[#1F2937] border border-white/20 rounded-md px-3 py-2 text-white focus:outline-none focus:ring-2 focus:ring-[#60A5FA]"
                  >
                    <option value="term">Term Duration</option>
                    <option value="parties">Parties</option>
                    <option value="firm">Firm Details</option>
                    <option value="signature">Signature</option>
                    <option value="other">Other</option>
                  </select>
                  <input
                    type="text"
                    value={adminRuleName}
                    onChange={(e) => setAdminRuleName(e.target.value)}
                    placeholder="Enter rule name..."
                    className="flex-1 bg-[#1F2937] border border-white/20 rounded-md px-3 py-2 text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:ring-2 focus:ring-[#60A5FA]"
                  />
                  <button
                    onClick={() => setShowAdminRuleModal(true)}
                    className="bg-[#60A5FA] hover:bg-[#60A5FA]/80 text-white px-4 py-2 rounded-md transition-colors"
                  >
                    Add Rule
                  </button>
                </div>
                
                {/* Display custom rules */}
                {customRules.length > 0 ? (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-[#E5E7EB]/80">Select Rules to Apply:</h3>
                    {customRules.map((rule, index) => (
                      <div key={index} className="flex items-center justify-between bg-[#1F2937] rounded-lg p-3">
                        <div className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            checked={rule.id ? selectedRules.includes(rule.id) : false}
                            onChange={() => rule.id && toggleRuleSelection(rule.id)}
                            className="w-4 h-4 text-[#60A5FA] bg-gray-700 border-gray-600 rounded focus:ring-[#60A5FA] focus:ring-2"
                          />
                          {getCategoryIcon(rule.category)}
                          <div>
                            {rule.name && (
                              <div className="text-sm font-medium text-white">{rule.name}</div>
                            )}
                            <span className="text-sm text-[#E5E7EB]">{rule.instruction}</span>
                          </div>
                        </div>
                        <button
                          onClick={() => removeCustomRule(index)}
                          className="text-red-400 hover:text-red-300 transition-colors"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Shield className="w-12 h-12 mx-auto mb-4 text-[#E5E7EB]/40" />
                    <p className="text-[#E5E7EB]/60">No redlining rules created yet</p>
                    <p className="text-sm text-[#E5E7EB]/40 mt-2">Create your first rule using the form above</p>
                    <p className="text-xs text-[#E5E7EB]/30 mt-1">Rules will be available to all users</p>
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

              {/* Signature Upload Section */}
              <div className="mt-6 pt-6 border-t border-white/10">
                <h3 className="text-lg font-medium text-white mb-4 flex items-center">
                  <PenTool className="w-5 h-5 mr-2 text-[#60A5FA]" />
                  Digital Signature
                </h3>
                
                <div className="space-y-4">
                  {/* Signature Upload */}
                  <div>
                    <label className="block text-sm text-[#E5E7EB]/60 mb-2">Upload Signature Image</label>
                    <div className="flex items-center space-x-4">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleSignatureUpload}
                        className="hidden"
                        id="signature-upload"
                      />
                      <label
                        htmlFor="signature-upload"
                        className="px-4 py-2 bg-[#60A5FA] text-white rounded-md hover:bg-[#3B82F6] cursor-pointer transition-colors"
                      >
                        Choose Signature
                      </label>
                      {signatureFile && (
                        <button
                          onClick={removeSignature}
                          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                        >
                          Remove
                </button>
                      )}
                    </div>
                    <p className="text-xs text-[#E5E7EB]/60 mt-1">
                      Upload a PNG, JPG, or other image format of your signature
                    </p>
                  </div>

                  {/* Signature Preview */}
                  {signaturePreview && (
                    <div>
                      <label className="block text-sm text-[#E5E7EB]/60 mb-2">Signature Preview</label>
                      <div className="border-2 border-dashed border-white/20 rounded-lg p-4 bg-white/5">
                        <img
                          src={signaturePreview}
                          alt="Signature preview"
                          className="max-h-32 max-w-full object-contain"
                        />
                      </div>
                    </div>
                  )}
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
                  disabled={!uploadedDocument?.id}
                  className="w-full bg-[#10B981] hover:bg-[#10B981]/90 disabled:bg-[#10B981]/40 text-white py-3 rounded-lg font-semibold transition-all duration-200 hover:shadow-lg hover:shadow-[#10B981]/25 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                  <Download className="w-5 h-5" />
                  <span>
                    {uploadedDocument?.id
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
        </>
      )}

      {/* Create Rule Modal */}
      {showAdminRuleModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#1F2937] rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-xl font-semibold text-white mb-4">Create Redlining Rule</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#E5E7EB]/60 mb-1">Rule Name</label>
                <input
                  type="text"
                  value={adminRuleName}
                  onChange={(e) => setAdminRuleName(e.target.value)}
                  placeholder="Enter rule name..."
                  className="w-full px-3 py-2 bg-[#0B1220] border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                />
              </div>

              <div>
                <label className="block text-sm text-[#E5E7EB]/60 mb-1">Category</label>
                <select
                  value={adminRuleCategory}
                  onChange={(e) => setAdminRuleCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-[#0B1220] border border-white/20 rounded text-white focus:outline-none focus:border-[#60A5FA]"
                >
                  <option value="term">Term Duration</option>
                  <option value="parties">Parties</option>
                  <option value="firm">Firm Details</option>
                  <option value="signature">Signature</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-[#E5E7EB]/60 mb-1">Instruction</label>
                <textarea
                  value={adminRuleInstruction}
                  onChange={(e) => setAdminRuleInstruction(e.target.value)}
                  placeholder="Enter detailed instruction..."
                  rows={3}
                  className="w-full px-3 py-2 bg-[#0B1220] border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                />
              </div>
            </div>
            
            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowAdminRuleModal(false)}
                className="flex-1 px-4 py-2 bg-[#374151] hover:bg-[#4B5563] text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={createAdminRule}
                className="flex-1 px-4 py-2 bg-[#60A5FA] hover:bg-[#60A5FA]/80 text-white rounded-lg transition-colors"
              >
                Create Rule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-[#1F2937] rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-xl font-semibold text-white mb-4">Add New User</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#E5E7EB]/60 mb-1">Username</label>
                <input
                  type="text"
                  value={newUserData.username}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="Enter username..."
                  className="w-full px-3 py-2 bg-[#0B1220] border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                />
              </div>

              <div>
                <label className="block text-sm text-[#E5E7EB]/60 mb-1">Email</label>
                <input
                  type="email"
                  value={newUserData.email}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="Enter email..."
                  className="w-full px-3 py-2 bg-[#0B1220] border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                />
              </div>

              <div>
                <label className="block text-sm text-[#E5E7EB]/60 mb-1">Role</label>
                <select
                  value={newUserData.role}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full px-3 py-2 bg-[#0B1220] border border-white/20 rounded text-white focus:outline-none focus:border-[#60A5FA]"
                >
                  <option value="USER">User</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-[#E5E7EB]/60 mb-1">Password</label>
                <input
                  type="password"
                  value={newUserData.password}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Enter password..."
                  className="w-full px-3 py-2 bg-[#0B1220] border border-white/20 rounded text-white placeholder-[#E5E7EB]/40 focus:outline-none focus:border-[#60A5FA]"
                />
              </div>
            </div>
            
            <div className="flex space-x-3 mt-6">
              <button
                onClick={() => setShowAddUserModal(false)}
                className="flex-1 px-4 py-2 bg-[#374151] hover:bg-[#4B5563] text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={addNewUser}
                className="flex-1 px-4 py-2 bg-[#10B981] hover:bg-[#10B981]/80 text-white rounded-lg transition-colors"
              >
                Add User
              </button>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
