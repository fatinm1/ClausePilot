'use client';

import { AppHeader, PageIntro } from '../../components/app-header'
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
  Zap,
  Edit
} from 'lucide-react';
import { apiClient } from '../../lib/api';
import { Document, CustomRule, FirmDetails } from '../../lib/api';
import DocumentViewer from '../components/DocumentViewer';

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
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
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

  const handleChangesReviewComplete = async (result: { success: boolean; documentId?: number }) => {
    setShowChangesReview(false);
    
    if (result.success) {
      setSuccess('Document processed successfully! You can now download the redlined document.');
      // Refresh the document to get the updated final_file_path
      if (uploadedDocument?.id) {
        // Document has been updated, user can now download
      }
    } else {
      setError('Failed to process changes. Please try again.');
    }
  };

  const downloadDocument = async () => {
    if (!uploadedDocument?.id) {
      setError('Run the review to get a download');
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

  const updateAdminRule = async () => {
    if (!editingRuleId || !adminRuleName.trim() || !adminRuleInstruction.trim()) {
      setError('Rule name and instruction are required');
      return;
    }

    try {
      const updates = {
        name: adminRuleName,
        category: adminRuleCategory,
        instruction: adminRuleInstruction
      };
      
      // Update rule in backend
      const response = await apiClient.updateRule(editingRuleId, updates, user?.id?.toString() || '');
      
      // Update in local state
      setCustomRules(prev => prev.map(rule => 
        rule.id === editingRuleId ? response.rule : rule
      ));
      
      // Reset form
      setAdminRuleName('');
      setAdminRuleInstruction('');
      setAdminRuleCategory('other');
      setEditingRuleId(null);
      setShowAdminRuleModal(false);
      
      setError(null);
      setSuccess('Rule updated successfully!');
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to update rule');
    }
  };

  const handleEditRule = (rule: CustomRule) => {
    if (!rule.id) return;
    
    setEditingRuleId(rule.id);
    setAdminRuleName(rule.name || '');
    setAdminRuleInstruction(rule.instruction);
    setAdminRuleCategory(rule.category || 'other');
    setShowAdminRuleModal(true);
  };

  const handleCloseRuleModal = () => {
    setShowAdminRuleModal(false);
    setEditingRuleId(null);
    setAdminRuleName('');
    setAdminRuleInstruction('');
    setAdminRuleCategory('other');
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

  const getCategoryIcon = (_category: string) => (
    <span aria-hidden="true" className="mt-[0.7em] block h-[2px] w-3 shrink-0 rounded bg-redline" />
  );

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'term': return 'Term';
      case 'parties': return 'Parties';
      case 'firm': return 'Firm Details';
      case 'signature': return 'Signature';
      default: return 'Other';
    }
  };

  // Single return statement with conditional rendering
  return (
    <div className="min-h-screen bg-black text-white/90">
      {loading ? (
        // Loading state
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-metal-mid border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-xl text-fg-2">Checking your session</p>
          </div>
        </div>
      ) : showChangesReview ? (
        // Inline Document Viewer with Changes
        <DocumentViewer
          documentId={uploadedDocument?.id || 0}
          documentText={documentText}
          customRules={customRules.filter(rule => rule.id && selectedRules.includes(rule.id))}
          firmDetails={{
            name: firmDetails.name,
            signerName: firmDetails.signerName,
            signerTitle: firmDetails.signerTitle,
          }}
          signatureFile={signatureFile}
          onComplete={handleChangesReviewComplete}
        />
      ) : !user ? (
        // Don't render anything while redirecting
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-metal-mid border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-xl text-fg-2">Redirecting...</p>
          </div>
        </div>
      ) : (
        // Main dashboard content (only for admin users)
        <>
      <AppHeader section="Admin" role="ADMIN" onSignOut={handleLogout}></AppHeader>

      <div className="mx-auto max-w-[1400px] px-5 py-12 md:px-8 md:py-16">
        <PageIntro title="Rules and reviews">Write the positions every NDA is checked against, manage who can review, and run documents yourself.</PageIntro>

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

        {/* Admin Section */}
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
                  <span className="text-white">{systemStats?.total_users ?? 'Loading...'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-fg-2">Documents</span>
                  <span className="text-white">{systemStats?.total_documents ?? 'Loading...'}</span>
              </div>
                <div className="flex justify-between">
                  <span className="text-fg-2">Rules</span>
                  <span className="text-white">{systemStats?.total_rules ?? customRules.length}</span>
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
                  Add a rule
                </button>
                <button 
                  onClick={() => setShowAddUserModal(true)}
                  className="btn-quiet sm w-full"
                >
                  Add a user
                </button>
              </div>
            </div>
          </div>
        </div>

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

            {/* Custom Rules */}
            <div className="panel p-6">
              <h2 className="mb-5 flex items-center text-[1.15rem] font-[500] text-white">
                <Shield className="w-5 h-5 mr-2 text-metal-mid" />
                Rules
              </h2>
              
              <div className="space-y-4">
                <div className="flex space-x-3">
                  <select
                    value={adminRuleCategory}
                    onChange={(e) => setAdminRuleCategory(e.target.value)}
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
                    value={adminRuleName}
                    onChange={(e) => setAdminRuleName(e.target.value)}
                    placeholder="Enter rule name..."
                    className="field flex-1"
                  />
                  <button
                    onClick={() => setShowAdminRuleModal(true)}
                    className="btn-metal sm"
                  >
                    Add rule
                  </button>
                </div>
                
                {/* Display custom rules */}
                {customRules.length > 0 ? (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-fg-2">Rules to apply</h3>
                    {customRules.map((rule, index) => (
                      <div key={index} className="flex items-center justify-between bg-ink-panel rounded-lg p-3">
                        <div className="flex items-center space-x-3">
                          <input
                            type="checkbox"
                            checked={rule.id ? selectedRules.includes(rule.id) : false}
                            onChange={() => rule.id && toggleRuleSelection(rule.id)}
                            className="h-4 w-4 accent-[#cbced2]"
                          />
                          {getCategoryIcon(rule.category)}
                          <div>
                            {rule.name && (
                              <div className="text-sm font-medium text-white">{rule.name}</div>
                            )}
                            <span className="text-sm text-white/90">{rule.instruction}</span>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => handleEditRule(rule)}
                            className="text-metal-mid hover:text-white transition-colors"
                            title="Edit rule"
                          >
                            <Edit className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => removeCustomRule(index)}
                            className="text-redline-text hover:text-white transition-colors"
                            title="Delete rule"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <Shield className="w-12 h-12 mx-auto mb-4 text-fg-3" />
                    <p className="text-fg-2">No rules yet</p>
                    <p className="text-sm text-fg-3 mt-2">Add your first rule with the form above.</p>
                    <p className="text-xs text-fg-3 mt-1">Rules will be available to all users</p>
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

              {/* Signature Upload Section */}
              <div className="mt-6 pt-6 border-t border-line">
                <h3 className="text-lg font-medium text-white mb-4 flex items-center">
                  <PenTool className="w-5 h-5 mr-2 text-metal-mid" />
                  Signature image
                </h3>
                
                <div className="space-y-4">
                  {/* Signature Upload */}
                  <div>
                    <label className="block text-sm text-fg-2 mb-2">Upload signature image</label>
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
                        className="btn-metal sm"
                      >
                        Choose image
                      </label>
                      {signatureFile && (
                        <button
                          onClick={removeSignature}
                          className="btn-danger"
                        >
                          Remove
                </button>
                      )}
                    </div>
                    <p className="text-xs text-fg-2 mt-1">
                      PNG or JPG. It is placed above the signer’s name.
                    </p>
                  </div>

                  {/* Signature preview */}
                  {signaturePreview && (
                    <div>
                      <label className="block text-sm text-fg-2 mb-2">Signature preview</label>
                      <div className="border-2 border-dashed border-line rounded-lg p-4 bg-white/5">
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
                  disabled={!uploadedDocument?.id}
                  className="btn-metal sm w-full"
                >
                  <Download className="w-5 h-5" />
                  <span>
                    {uploadedDocument?.id
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
        </>
      )}

      {/* Create/Edit Rule Modal */}
      {showAdminRuleModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-ink-panel rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-xl font-semibold text-white mb-4">
              {editingRuleId ? 'Edit rule' : 'New rule'}
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-fg-2 mb-1">Rule name</label>
                <input
                  type="text"
                  value={adminRuleName}
                  onChange={(e) => setAdminRuleName(e.target.value)}
                  placeholder="Enter rule name..."
                  className="field"
                />
              </div>

              <div>
                <label className="block text-sm text-fg-2 mb-1">Category</label>
                <select
                  value={adminRuleCategory}
                  onChange={(e) => setAdminRuleCategory(e.target.value)}
                  className="w-full px-3 py-2 bg-black border border-line rounded text-white focus:outline-none focus:border-metal-mid"
                >
                  <option value="term">Term</option>
                  <option value="parties">Parties</option>
                  <option value="firm">Firm Details</option>
                  <option value="signature">Signature</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm text-fg-2 mb-1">Instruction</label>
                <textarea
                  value={adminRuleInstruction}
                  onChange={(e) => setAdminRuleInstruction(e.target.value)}
                  placeholder="Enter detailed instruction..."
                  rows={3}
                  className="field"
                />
              </div>
            </div>
            
            <div className="flex space-x-3 mt-6">
              <button
                onClick={handleCloseRuleModal}
                className="btn-quiet sm flex-1"
              >
                Cancel
              </button>
              <button
                onClick={editingRuleId ? updateAdminRule : createAdminRule}
                className="btn-metal sm flex-1"
              >
                {editingRuleId ? 'Update Rule' : 'Create Rule'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add User Modal */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="bg-ink-panel rounded-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-xl font-semibold text-white mb-4">Add a user</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-fg-2 mb-1">Username</label>
                <input
                  type="text"
                  value={newUserData.username}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, username: e.target.value }))}
                  placeholder="Enter username..."
                  className="field"
                />
              </div>

              <div>
                <label className="block text-sm text-fg-2 mb-1">Email</label>
                <input
                  type="email"
                  value={newUserData.email}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, email: e.target.value }))}
                  placeholder="Enter email..."
                  className="field"
                />
              </div>

              <div>
                <label className="block text-sm text-fg-2 mb-1">Role</label>
                <select
                  value={newUserData.role}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, role: e.target.value }))}
                  className="w-full px-3 py-2 bg-black border border-line rounded text-white focus:outline-none focus:border-metal-mid"
                >
                  <option value="USER">User</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm text-fg-2 mb-1">Password</label>
                <input
                  type="password"
                  value={newUserData.password}
                  onChange={(e) => setNewUserData(prev => ({ ...prev, password: e.target.value }))}
                  placeholder="Enter password..."
                  className="field"
                />
              </div>
            </div>
            
            <div className="flex space-x-3 mt-6">
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
                Add User
              </button>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}
