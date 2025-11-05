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
  const [documentHtml, setDocumentHtml] = useState<string>('');

  // Generate changes when component mounts
  useEffect(() => {
    loadDocumentAndGenerateChanges();
  }, []);

  // Update HTML when changes status changes
  useEffect(() => {
    if (documentHtml && changes.length > 0) {
      updateDocumentDisplay();
    }
  }, [changes]);

  const loadDocumentAndGenerateChanges = async () => {
    try {
      setLoading(true);
      setError(null);

      // First, get the document with HTML formatting
      const docResponse = await fetch(`/v1/documents/${documentId}/text`, {
        headers: {
          'X-User-ID': '1',
        },
        credentials: 'include',
      });

      if (!docResponse.ok) {
        throw new Error('Failed to load document');
      }

      const docData = await docResponse.json();
      const html = docData.html || '';
      const text = docData.text || documentText;
      
      // Generate changes
      const changesResponse = await fetch(`/v1/changes/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1',
        },
        credentials: 'include',
        body: JSON.stringify({
          document_text: text,
          custom_rules: selectedRules.map(id => ({ id })),
          firm_details: firmDetails,
        }),
      });

      if (!changesResponse.ok) {
        throw new Error('Failed to generate changes');
      }

      const changesData = await changesResponse.json();
      const generatedChanges = changesData.changes.map((c: any) => ({
        ...c,
        status: 'pending',
      }));
      
      setChanges(generatedChanges);
      setDocumentHtml(injectChangesIntoHtml(html, generatedChanges));
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate changes');
    } finally {
      setLoading(false);
    }
  };

  const injectChangesIntoHtml = (html: string, changesList: Change[]): string => {
    // Inject change markers into the HTML
    let modifiedHtml = html;
    
    changesList.forEach((change) => {
      const oldText = change.current_text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
      
      const newText = change.new_text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;');
      
      // Create the replacement HTML with change markers and inline buttons
      const acceptBtn = `<button data-action="accept" data-change-id="${change.id}" style="padding: 4px 6px; background: rgba(34, 197, 94, 0.2); color: rgb(34, 197, 94); border: none; border-radius: 4px; cursor: pointer; font-size: 10px; margin-left: 6px;">✓</button>`;
      const rejectBtn = `<button data-action="reject" data-change-id="${change.id}" style="padding: 4px 6px; background: rgba(239, 68, 68, 0.2); color: rgb(239, 68, 68); border: none; border-radius: 4px; cursor: pointer; font-size: 10px; margin-left: 2px;">✗</button>`;
      
      const replacement = `<span class="change-container" data-change-id="${change.id}">` +
        `<span class="old-text" style="text-decoration: line-through; color: #000;">${oldText}</span>` +
        `<span class="new-text" style="text-decoration: underline; color: #DC2626; font-weight: 500;">${newText}</span>` +
        acceptBtn + rejectBtn +
        `</span>`;
      
      // Replace the old text in the HTML
      modifiedHtml = modifiedHtml.replace(oldText, replacement);
    });
    
    return modifiedHtml;
  };

  const updateDocumentDisplay = () => {
    // Re-inject changes based on current status
    // This is a simplified version - just re-fetch the document HTML would be better
    // For now, we'll rely on CSS to hide/show based on data attributes
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

  const handleDocumentClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    
    // Check if clicked on accept/reject button
    const button = target.closest('[data-action]');
    if (button) {
      const action = button.getAttribute('data-action');
      const changeId = button.getAttribute('data-change-id');
      
      if (changeId) {
        if (action === 'accept') {
          handleAccept(changeId);
        } else if (action === 'reject') {
          handleReject(changeId);
        }
      }
    }
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
      {/* Inline CSS for document styling */}
      <style jsx>{`
        .document-content * {
          color: #000000 !important;
        }
        .document-content p {
          margin-bottom: 10pt;
          line-height: 1.15;
          text-align: justify;
        }
        .document-content .change-container .old-text {
          color: #000000 !important;
        }
        .document-content .change-container .new-text {
          color: #DC2626 !important;
        }
      `}</style>
      
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
        fontSize: '12pt', 
        lineHeight: '1.6',
        color: '#000000',  // Force black text
      }}>
        <div 
          dangerouslySetInnerHTML={{ __html: documentHtml }}
          onClick={handleDocumentClick}
          style={{ color: '#000000' }}  // Force black text in content
          className="document-content"
        />
        
        {/* Fallback paragraph rendering if HTML not available */}
        {!documentHtml && (
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
        )}
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

