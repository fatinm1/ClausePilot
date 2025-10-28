const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5001');

export interface Document {
  id: number
  filename: string
  original_filename: string
  file_path: string
  file_size: number
  output_path?: string
  final_file_path?: string
  status: string
  user_id: number
  uploaded_at: string
  processed_at?: string
  error_message?: string
}

export interface CustomRule {
  id?: number;
  name?: string;
  category: string;
  instruction: string;
}

export interface FirmDetails {
  name: string
  address: string
  city: string
  state: string
  zipCode: string
  signerName: string
  signerTitle: string
  email: string
  phone: string
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      credentials: 'include',
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Document endpoints
  async uploadDocument(file: File, userId: string): Promise<{ message: string; document: Document }> {
    const formData = new FormData();
    formData.append('file', file);
    
    return this.request<{ message: string; document: Document }>('/v1/documents/upload', {
      method: 'POST',
      headers: {
        'X-User-ID': userId,
      },
      body: formData,
    });
  }

  async processDocument(
    documentId: number,
    customRules: CustomRule[],
    firmDetails: FirmDetails,
    userId: string,
    signatureFile?: File
  ): Promise<{ message: string; document: Document; processing_result: any }> {
    // If signature file is provided, upload it first
    let signaturePath = null;
    if (signatureFile) {
      const signatureUpload = await this.uploadSignature(signatureFile, userId);
      signaturePath = signatureUpload.signature_path;
    }

    const payload = {
      custom_rules: customRules,
      firm_details: firmDetails,
      signature_path: signaturePath,
    };
    
    // DEBUG: Log the payload being sent to backend
    console.log('🌐 API Client: Sending to backend:', payload);
    console.log('🌐 API Client: Firm details being sent:', firmDetails);
    
    return this.request<{ message: string; document: Document; processing_result: any }>(
      `/v1/documents/${documentId}/process`,
      {
        method: 'POST',
        headers: {
          'X-User-ID': userId,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    );
  }

  async uploadSignature(file: File, userId: string): Promise<{ message: string; signature_path: string }> {
    const formData = new FormData();
    formData.append('signature', file);
    
    return this.request<{ message: string; signature_path: string }>('/v1/signatures/upload', {
      method: 'POST',
      headers: {
        'X-User-ID': userId,
      },
      body: formData,
    });
  }

  async getDocument(documentId: number, userId: string): Promise<{ document: Document; processing_jobs: any[] }> { // ProcessingJob interface removed, so using 'any' for now
    return this.request<{ document: Document; processing_jobs: any[] }>(
      `/v1/documents/${documentId}`,
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async listDocuments(userId: string, page = 1, perPage = 10): Promise<{
    documents: Document[];
    pagination: { page: number; per_page: number; total: number; pages: number };
  }> {
    return this.request<{
      documents: Document[];
      pagination: { page: number; per_page: number; total: number; pages: number };
    }>(
      `/v1/documents?page=${page}&per_page=${perPage}`,
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async deleteDocument(documentId: number, userId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/v1/documents/${documentId}`,
      {
        method: 'DELETE',
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async downloadDocument(documentId: number, userId: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/v1/documents/${documentId}/download`, {
        method: 'GET',
        headers: {
          'X-User-ID': userId,
        },
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      // Get the filename from the response headers or use a default
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'redlined-nda.docx';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create a blob and download it
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      throw error;
    }
  }

  async getDocumentText(documentId: number): Promise<{ text: string }> {
    const response = await this.request<{ text: string }>(
      `/v1/documents/${documentId}/text`,
      {
        method: 'GET',
        headers: {
          'X-User-ID': '1', // Mock user ID for demo
        },
      }
    );
    return response;
  }

  // Processing rules endpoints
  async listRules(userId: string): Promise<{ rules: any[] }> {
    return this.request<{ rules: any[] }>('/v1/rules/', {
      headers: {
        'X-User-ID': userId,
      },
    });
  }

  async createRule(rule: any, userId: string): Promise<any> { // ProcessingRule interface removed, so using 'any' for now
    const response = await fetch(`${this.baseUrl}/v1/rules/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId
      },
      body: JSON.stringify(rule)
    })
    
    if (!response.ok) {
      throw new Error(`Failed to create rule: ${response.statusText}`)
    }
    
    return response.json()
  }

  async updateRule(
    ruleId: number,
    updates: Partial<any>, // ProcessingRule interface removed, so using 'any' for now
    userId: string
  ): Promise<{ message: string; rule: any }> { // ProcessingRule interface removed, so using 'any' for now
    return this.request<{ message: string; rule: any }>(
      `/v1/rules/${ruleId}`,
      {
        method: 'PUT',
        headers: {
          'X-User-ID': userId,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      }
    );
  }

  async deleteRule(ruleId: number, userId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/v1/rules/${ruleId}`,
      {
        method: 'DELETE',
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async getRuleCategories(userId: string): Promise<{ categories: Array<{ value: string; label: string; description: string }> }> {
    return this.request<{ categories: Array<{ value: string; label: string; description: string }> }>(
      '/v1/rules/categories',
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async getRuleTemplates(userId: string): Promise<{ templates: Array<{ name: string; instruction: string; category: string; description: string }> }> {
    return this.request<{ templates: Array<{ name: string; instruction: string; category: string; description: string }> }>(
      '/v1/rules/templates',
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  // Admin endpoints
  async listUsers(userId: string): Promise<{ users: Array<{ id: number; email: string; role: string; is_active: boolean; created_at: string }> }> {
    return this.request<{ users: Array<{ id: number; email: string; role: string; is_active: boolean; created_at: string }> }>(
      '/v1/admin/users',
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async createUser(userId: string, userData: { email: string; password: string; role?: string }): Promise<{ message: string; user: any }> {
    return this.request<{ message: string; user: any }>(
      '/v1/admin/users',
      {
        method: 'POST',
        headers: {
          'X-User-ID': userId,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(userData),
      }
    );
  }

  async updateUser(userId: string, targetUserId: number, updates: Partial<{ email: string; role: string; is_active: boolean; password: string }>): Promise<{ message: string; user: any }> {
    return this.request<{ message: string; user: any }>(
      `/v1/admin/users/${targetUserId}`,
      {
        method: 'PUT',
        headers: {
          'X-User-ID': userId,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      }
    );
  }

  async deleteUser(userId: string, targetUserId: number): Promise<{ message: string }> {
    return this.request<{ message: string }>(
      `/v1/admin/users/${targetUserId}`,
      {
        method: 'DELETE',
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async getAdminDashboard(userId: string): Promise<{
    statistics: { total_users: number; total_documents: number; total_rules: number; global_rules: number };
    recent_activity: { documents: any[]; users: any[] };
  }> {
    return this.request<{
      statistics: { total_users: number; total_documents: number; total_rules: number; global_rules: number };
      recent_activity: { documents: any[]; users: any[] };
    }>(
      '/v1/admin/dashboard',
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }

  async getSystemHealth(userId: string): Promise<{ database: string; file_system: string; timestamp: string }> {
    return this.request<{ database: string; file_system: string; timestamp: string }>(
      '/v1/admin/system/health',
      {
        headers: {
          'X-User-ID': userId,
        },
      }
    );
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
