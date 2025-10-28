'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';

interface Change {
  id: string;
  type: string;
  section: string;
  current_text: string;
  new_text: string;
  reason: string;
  location_hint: string;
  status: 'pending' | 'accepted' | 'rejected';
  order: number;
}

interface ChangesReviewProps {
  documentId: number;
  documentText: string;
  customRules: any[];
  firmDetails: any;
  onComplete: (finalDocumentPath: string) => void;
}

export default function ChangesReview({
  documentId,
  documentText,
  customRules,
  firmDetails,
  onComplete
}: ChangesReviewProps) {
  const [changes, setChanges] = useState<Change[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    generateChanges();
  }, []);

  const generateChanges = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await api.post('/v1/changes/generate', {
        document_text: documentText,
        custom_rules: customRules,
        firm_details: firmDetails
      });

      if (response.data.success) {
        setChanges(response.data.changes);
      } else {
        setError('Failed to generate changes');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to generate changes');
    } finally {
      setLoading(false);
    }
  };

  const updateChangeStatus = (changeId: string, status: 'accepted' | 'rejected') => {
    setChanges(prev => prev.map(change => 
      change.id === changeId ? { ...change, status } : change
    ));
  };

  const acceptAllChanges = () => {
    setChanges(prev => prev.map(change => ({ ...change, status: 'accepted' as const })));
  };

  const rejectAllChanges = () => {
    setChanges(prev => prev.map(change => ({ ...change, status: 'rejected' as const })));
  };

  const applyAcceptedChanges = async () => {
    try {
      setApplying(true);
      setError(null);

      const acceptedChanges = changes.filter(change => change.status === 'accepted');
      
      if (acceptedChanges.length === 0) {
        setError('No changes selected for application');
        return;
      }

      const response = await api.post(`/v1/changes/apply-accepted/${documentId}`, {
        accepted_changes: acceptedChanges
      });

      if (response.data.success) {
        onComplete(response.data.final_document_path);
      } else {
        setError('Failed to apply changes');
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to apply changes');
    } finally {
      setApplying(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'accepted': return 'text-green-600 bg-green-100';
      case 'rejected': return 'text-red-600 bg-red-100';
      default: return 'text-yellow-600 bg-yellow-100';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'accepted': return '✓';
      case 'rejected': return '✗';
      default: return '?';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Generating changes for review...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-center">
          <div className="text-red-600 text-xl mr-3">⚠️</div>
          <div>
            <h3 className="text-red-800 font-semibold">Error</h3>
            <p className="text-red-700">{error}</p>
            <button 
              onClick={generateChanges}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        {/* Header */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Review Changes</h2>
              <p className="text-gray-600 mt-1">
                Review and accept/reject {changes.length} proposed changes
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={acceptAllChanges}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Accept All
              </button>
              <button
                onClick={rejectAllChanges}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Reject All
              </button>
            </div>
          </div>
        </div>

        {/* Changes List */}
        <div className="p-6">
          {changes.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500">No changes to review</p>
            </div>
          ) : (
            <div className="space-y-4">
              {changes.map((change) => (
                <div key={change.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-3">
                        <span className="text-sm font-medium text-gray-500">
                          Change #{change.order}
                        </span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(change.status)}`}>
                          {getStatusIcon(change.status)} {change.status}
                        </span>
                        <span className="text-sm text-gray-500">
                          {change.section} • {change.type}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            Current Text
                          </label>
                          <div className="bg-gray-50 p-3 rounded border">
                            <span className="line-through text-gray-600">
                              {change.current_text}
                            </span>
                          </div>
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">
                            New Text
                          </label>
                          <div className="bg-green-50 p-3 rounded border border-green-200">
                            <span className="text-green-800 underline">
                              {change.new_text}
                            </span>
                          </div>
                        </div>
                      </div>
                      
                      <div className="text-sm text-gray-600">
                        <p><strong>Reason:</strong> {change.reason}</p>
                        {change.location_hint && (
                          <p><strong>Location:</strong> {change.location_hint}</p>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex flex-col space-y-2 ml-4">
                      <button
                        onClick={() => updateChangeStatus(change.id, 'accepted')}
                        className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                          change.status === 'accepted'
                            ? 'bg-green-600 text-white'
                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                        }`}
                      >
                        Accept
                      </button>
                      <button
                        onClick={() => updateChangeStatus(change.id, 'rejected')}
                        className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                          change.status === 'rejected'
                            ? 'bg-red-600 text-white'
                            : 'bg-red-100 text-red-700 hover:bg-red-200'
                        }`}
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              <span className="font-medium">
                {changes.filter(c => c.status === 'accepted').length} accepted
              </span>
              {' • '}
              <span className="font-medium">
                {changes.filter(c => c.status === 'rejected').length} rejected
              </span>
              {' • '}
              <span className="font-medium">
                {changes.filter(c => c.status === 'pending').length} pending
              </span>
            </div>
            <button
              onClick={applyAcceptedChanges}
              disabled={applying || changes.filter(c => c.status === 'accepted').length === 0}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {applying ? 'Applying...' : 'Apply Accepted Changes'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
