'use client';

import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, Download, Loader } from 'lucide-react';

interface Change {
  id: string;
  type: string;
  section: string;
  current_text: string;
  new_text: string;
  reason: string;
  location_hint: string;
  status: 'pending' | 'accepted' | 'rejected';
}

interface DocumentViewerProps {
  documentId: number;
  documentText: string;
  onComplete: (result: { success: boolean; documentId?: number }) => void;
  firmDetails: {
    name: string;
    signerName: string;
    signerTitle: string;
  };
  selectedRules: number[];
}

export default function DocumentViewer({ documentId, documentText, onComplete, firmDetails, selectedRules }: DocumentViewerProps) {
  const [changes, setChanges] = useState<Change[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documentSegments, setDocumentSegments] = useState<any[]>([]);

  // Generate changes when component mounts
  useEffect(() => {
    generateChanges();
  }, []);

  const generateChanges = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`/v1/changes/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1',
        },
        credentials: 'include',
        body: JSON.stringify({
          document_text: documentText,
          custom_rules: selectedRules.map(id => ({ id })),
          firm_details: firmDetails,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to generate changes');
      }

      const data = await response.json();
      const generatedChanges = data.changes.map((c: any) => ({
        ...c,
        status: 'pending',
      }));
      
      setChanges(generatedChanges);
      buildDocumentSegments(documentText, generatedChanges);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate changes');
    } finally {
      setLoading(false);
    }
  };

  const buildDocumentSegments = (text: string, changesList: Change[]) => {
    // Split document into paragraphs first to preserve structure
    const paragraphs = text.split('\n');
    const allSegments: any[] = [];
    
    // Sort changes by their position in the document
    const sortedChanges = [...changesList].sort((a, b) => {
      const posA = text.indexOf(a.current_text);
      const posB = text.indexOf(b.current_text);
      return posA - posB;
    });

    let globalPos = 0;
    
    paragraphs.forEach((paragraph, paraIdx) => {
      const paragraphSegments: any[] = [];
      let currentPos = 0;
      
      // Find changes that belong to this paragraph
      sortedChanges.forEach((change) => {
        const changePos = paragraph.indexOf(change.current_text, currentPos);
        
        if (changePos !== -1) {
          // Add text before the change
          if (changePos > currentPos) {
            paragraphSegments.push({
              type: 'text',
              content: paragraph.substring(currentPos, changePos),
            });
          }
          
          // Add the change
          paragraphSegments.push({
            type: 'change',
            change: change,
          });
          
          currentPos = changePos + change.current_text.length;
        }
      });

      // Add remaining text in paragraph
      if (currentPos < paragraph.length) {
        paragraphSegments.push({
          type: 'text',
          content: paragraph.substring(currentPos),
        });
      }
      
      // Add paragraph as a unit
      allSegments.push({
        type: 'paragraph',
        segments: paragraphSegments,
        isEmpty: paragraph.trim().length === 0,
      });
      
      globalPos += paragraph.length + 1; // +1 for newline
    });

    setDocumentSegments(allSegments);
  };

  const handleAccept = (changeId: string) => {
    setChanges((prev) =>
      prev.map((c) =>
        c.id === changeId ? { ...c, status: 'accepted' } : c
      )
    );
  };

  const handleReject = (changeId: string) => {
    setChanges((prev) =>
      prev.map((c) =>
        c.id === changeId ? { ...c, status: 'rejected' } : c
      )
    );
  };

  const handleAcceptAll = () => {
    setChanges((prev) => prev.map((c) => ({ ...c, status: 'accepted' })));
  };

  const handleRejectAll = () => {
    setChanges((prev) => prev.map((c) => ({ ...c, status: 'rejected' })));
  };

  const applyChanges = async () => {
    try {
      setApplying(true);
      setError(null);

      const response = await fetch(`/v1/changes/apply-accepted/${documentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1',
        },
        credentials: 'include',
        body: JSON.stringify({
          changes: changes,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to apply changes');
      }

      const result = await response.json();
      onComplete({ success: true, documentId });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply changes');
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <Loader className="w-12 h-12 text-[#60A5FA] animate-spin mx-auto mb-4" />
          <p className="text-[#E5E7EB]">Analyzing document and generating changes...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-6">
        <p className="text-red-400">{error}</p>
        <button
          onClick={() => onComplete({ success: false })}
          className="mt-4 px-4 py-2 bg-[#60A5FA] text-white rounded-lg hover:bg-[#60A5FA]/90"
        >
          Go Back
        </button>
      </div>
    );
  }

  const acceptedCount = changes.filter((c) => c.status === 'accepted').length;
  const rejectedCount = changes.filter((c) => c.status === 'rejected').length;
  const pendingCount = changes.filter((c) => c.status === 'pending').length;

  return (
    <div className="space-y-6">
      {/* Header with actions */}
      <div className="bg-white/5 border border-white/10 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-white mb-2">Review Changes</h2>
            <p className="text-[#E5E7EB]/80">
              Review changes in the document below. Click accept or reject for each change.
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <div className="text-sm text-[#E5E7EB]/60">
              <span className="text-green-400 font-semibold">{acceptedCount}</span> Accepted •{' '}
              <span className="text-red-400 font-semibold">{rejectedCount}</span> Rejected •{' '}
              <span className="text-yellow-400 font-semibold">{pendingCount}</span> Pending
            </div>
          </div>
        </div>

        {/* Bulk actions */}
        <div className="flex space-x-3">
          <button
            onClick={handleAcceptAll}
            className="px-4 py-2 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg hover:bg-green-500/30 transition-colors"
          >
            Accept All Changes
          </button>
          <button
            onClick={handleRejectAll}
            className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30 transition-colors"
          >
            Reject All Changes
          </button>
          <button
            onClick={applyChanges}
            disabled={applying || pendingCount > 0}
            className="ml-auto px-6 py-2 bg-[#60A5FA] text-white rounded-lg hover:bg-[#60A5FA]/90 disabled:bg-[#60A5FA]/40 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {applying ? (
              <>
                <Loader className="w-5 h-5 animate-spin" />
                <span>Applying...</span>
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                <span>
                  {pendingCount > 0
                    ? `Review ${pendingCount} pending change${pendingCount !== 1 ? 's' : ''}`
                    : 'Generate Final Document'}
                </span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Document viewer with inline changes */}
      <div className="bg-white rounded-lg shadow-2xl p-12 max-w-5xl mx-auto" style={{ 
        fontFamily: 'Times New Roman, serif', 
        fontSize: '11pt', 
        lineHeight: '1.5',
        whiteSpace: 'pre-wrap',  // Preserve whitespace and tabs
      }}>
        <div>
          {documentSegments.map((para, paraIdx) => {
            if (para.type === 'paragraph') {
              // Render empty paragraphs as line breaks
              if (para.isEmpty) {
                return <div key={paraIdx} style={{ height: '1em' }} />;
              }
              
              return (
                <p key={paraIdx} className="text-black" style={{ 
                  marginBottom: '0.75em',
                  textIndent: para.segments[0]?.content?.startsWith('\t') ? '2em' : '0',
                  whiteSpace: 'pre-wrap',  // Preserve tabs and spaces
                }}>
                  {para.segments.map((segment: any, segIdx: number) => {
                    if (segment.type === 'text') {
                      return (
                        <span key={segIdx}>
                          {segment.content}
                        </span>
                      );
                    } else if (segment.type === 'change') {
                      const change = segment.change;
                      const isAccepted = change.status === 'accepted';
                      const isRejected = change.status === 'rejected';
                      
                      return (
                        <span key={segIdx} className="inline-block">
                          {/* Old text with strikethrough */}
                          <span
                            className="text-black"
                            style={{
                              textDecoration: 'line-through',
                              display: isAccepted ? 'none' : 'inline',
                            }}
                          >
                            {change.current_text}
                          </span>
                          
                          {/* New text with underline */}
                          <span
                            className="text-red-600"
                            style={{
                              textDecoration: 'underline',
                              fontWeight: 500,
                              display: isRejected ? 'none' : 'inline',
                            }}
                          >
                            {change.new_text}
                          </span>
                          
                          {/* Inline accept/reject buttons */}
                          {change.status === 'pending' && (
                            <span className="inline-flex items-center ml-2 space-x-1 align-middle">
                              <button
                                onClick={() => handleAccept(change.id)}
                                className="p-0.5 bg-green-500/20 text-green-600 rounded hover:bg-green-500/30 transition-colors"
                                title="Accept change"
                              >
                                <CheckCircle className="w-3 h-3" />
                              </button>
                              <button
                                onClick={() => handleReject(change.id)}
                                className="p-0.5 bg-red-500/20 text-red-600 rounded hover:bg-red-500/30 transition-colors"
                                title="Reject change"
                              >
                                <XCircle className="w-3 h-3" />
                              </button>
                            </span>
                          )}
                          
                          {/* Status indicator */}
                          {change.status === 'accepted' && (
                            <span className="inline-flex items-center ml-1">
                              <CheckCircle className="w-3 h-3 text-green-500" />
                            </span>
                          )}
                          {change.status === 'rejected' && (
                            <span className="inline-flex items-center ml-1">
                              <XCircle className="w-3 h-3 text-red-500" />
                            </span>
                          )}
                        </span>
                      );
                    }
                    return null;
                  })}
                </p>
              );
            }
            return null;
          })}
        </div>
      </div>

      {/* Change summary sidebar */}
      <div className="bg-white/5 border border-white/10 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Changes Summary</h3>
        <div className="space-y-2">
          {changes.map((change, idx) => (
            <div
              key={change.id}
              className={`p-3 rounded-lg border ${
                change.status === 'accepted'
                  ? 'bg-green-500/10 border-green-500/30'
                  : change.status === 'rejected'
                  ? 'bg-red-500/10 border-red-500/30'
                  : 'bg-white/5 border-white/10'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="text-sm font-medium text-white mb-1">
                    Change {idx + 1}: {change.section}
                  </div>
                  <div className="text-xs text-[#E5E7EB]/60">
                    {change.reason}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {change.status === 'pending' && (
                    <>
                      <button
                        onClick={() => handleAccept(change.id)}
                        className="p-1 bg-green-500/20 text-green-400 rounded hover:bg-green-500/30"
                      >
                        <CheckCircle className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleReject(change.id)}
                        className="p-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30"
                      >
                        <XCircle className="w-5 h-5" />
                      </button>
                    </>
                  )}
                  {change.status === 'accepted' && (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  )}
                  {change.status === 'rejected' && (
                    <XCircle className="w-5 h-5 text-red-500" />
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

