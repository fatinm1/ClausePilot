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

interface CustomRule {
  id?: number;
  name?: string;
  category: string;
  instruction: string;
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
  customRules: CustomRule[];
}

export default function DocumentViewer({ documentId, documentText, onComplete, firmDetails, customRules }: DocumentViewerProps) {
  const [changes, setChanges] = useState<Change[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documentHtml, setDocumentHtml] = useState<string>('');
  const [originalHtml, setOriginalHtml] = useState<string>(''); // Cache original HTML

  // Generate changes when component mounts
  useEffect(() => {
    loadDocumentAndGenerateChanges();
  }, []);

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
      
      // Document loaded successfully
      
      // Cache the original HTML for fast regeneration
      setOriginalHtml(html);
      
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
          custom_rules: customRules,
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
      const injectedHtml = injectChangesIntoHtml(html, generatedChanges);
      // Changes injected into HTML
      setDocumentHtml(injectedHtml);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate changes');
    } finally {
      setLoading(false);
    }
  };

  const injectChangesIntoHtml = (html: string, changesList: Change[]): string => {
    let modifiedHtml = html;
    
    changesList.forEach((change, idx) => {
      const escapeRegex = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      
      // Build a VERY flexible regex that allows ANY HTML tags/whitespace between characters
      const textChars = change.current_text.split('');
      const pattern = textChars.map((char, charIdx) => {
        if (char === ' ' || char === '\t') {
          // For whitespace: match any combination of spans, nbsp, spaces
          // Allow multiple span tags in between
          return '(?:</span>)?(?:<span[^>]*>)*(?:&nbsp;|\\s)+(?:</span>)?(?:<span[^>]*>)*';
        } else if (char === '_') {
          // Underscores might be repeated (e.g., "_______")
          const escaped = escapeRegex(char);
          return `(?:</span>)?(?:<span[^>]*>)*${escaped}+(?:</span>)?(?:<span[^>]*>)*`;
        } else {
          // Regular character: allow span tags before and after
          const escaped = escapeRegex(char).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          return `(?:</span>)?(?:<span[^>]*>)*${escaped}(?:</span>)?(?:<span[^>]*>)*`;
        }
      }).join('');
      
      const regex = new RegExp(pattern, 'i');
      let match = modifiedHtml.match(regex);
      
      // FALLBACK for signature fields: If regex fails, use simple label search
      if (!match && (change.current_text.startsWith('By:') || change.current_text.startsWith('Title:') || change.current_text.startsWith('For:') || change.current_text.startsWith('Date:'))) {
        const label = change.current_text.split(':')[0] + ':';
        const labelIndex = modifiedHtml.indexOf(label);
        if (labelIndex !== -1) {
          let endIndex = modifiedHtml.indexOf('</p>', labelIndex);
          if (endIndex === -1) endIndex = labelIndex + 400;
          match = [modifiedHtml.substring(labelIndex, endIndex)];
        }
      }
      
      if (match) {
        const matchedText = match[0];
        
        // Escape the new text for HTML
        const newTextEscaped = change.new_text
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;');
        
        // Create LARGE, VISIBLE inline buttons
        const acceptBtn = `<button data-action="accept" data-change-id="${change.id}" style="display: inline-block; padding: 6px 12px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.4), rgba(34, 197, 94, 0.3)); color: rgb(22, 163, 74); border: 2px solid rgb(34, 197, 94); border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: bold; margin-left: 12px; vertical-align: middle; box-shadow: 0 2px 4px rgba(34, 197, 94, 0.3); transition: all 0.2s;">✓ Accept</button>`;
        const rejectBtn = `<button data-action="reject" data-change-id="${change.id}" style="display: inline-block; padding: 6px 12px; background: linear-gradient(135deg, rgba(239, 68, 68, 0.4), rgba(239, 68, 68, 0.3)); color: rgb(220, 38, 38); border: 2px solid rgb(239, 68, 68); border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: bold; margin-left: 8px; vertical-align: middle; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3); transition: all 0.2s;">✗ Reject</button>`;
        
        const replacement = `<span class="change-container" data-change-id="${change.id}" style="background: rgba(255, 255, 0, 0.2); padding: 4px 6px; border-radius: 4px; display: inline; border: 1px dashed rgba(255, 193, 7, 0.5);">` +
          `<span class="old-text" style="text-decoration: line-through; color: #000000;">${matchedText}</span>` +
          `<span class="new-text" style="text-decoration: underline; color: #DC2626; font-weight: 600;">${newTextEscaped}</span>` +
          acceptBtn + rejectBtn +
          `</span>`;
        
        modifiedHtml = modifiedHtml.replace(matchedText, replacement);
      }
    });
    
    return modifiedHtml;
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
    // Instantly update DOM (no React re-render!)
    const container = document.querySelector(`.change-container[data-change-id="${changeId}"]`) as HTMLElement;
    if (!container) return;
    
    const oldTextSpan = container.querySelector('.old-text') as HTMLElement;
    const newTextSpan = container.querySelector('.new-text') as HTMLElement;
    const acceptBtn = container.querySelector('button[data-action="accept"]') as HTMLElement;
    const rejectBtn = container.querySelector('button[data-action="reject"]') as HTMLElement;
    
    // Remove highlight and hide old text
    container.style.background = 'transparent';
    container.style.border = 'none';
    if (oldTextSpan) oldTextSpan.style.display = 'none';
    if (newTextSpan) {
      newTextSpan.style.textDecoration = 'none';
      newTextSpan.style.color = '#000000';
      newTextSpan.style.fontWeight = 'normal';
    }
    
    // Remove buttons and add checkmark
    if (acceptBtn) acceptBtn.remove();
    if (rejectBtn) rejectBtn.remove();
    const statusSpan = document.createElement('span');
    statusSpan.style.cssText = 'color: #22C55E; margin-left: 8px; font-size: 14px; font-weight: bold;';
    statusSpan.textContent = '✓ Accepted';
    container.appendChild(statusSpan);
    
    // Update state WITHOUT triggering re-render (update in-place for later use)
    const changeIndex = changes.findIndex(c => c.id === changeId);
    if (changeIndex !== -1) {
      changes[changeIndex].status = 'accepted';
    }
  };

  const handleReject = (changeId: string) => {
    // Instantly update DOM (no React re-render!)
    const container = document.querySelector(`.change-container[data-change-id="${changeId}"]`) as HTMLElement;
    if (!container) return;
    
    const oldTextSpan = container.querySelector('.old-text') as HTMLElement;
    const newTextSpan = container.querySelector('.new-text') as HTMLElement;
    const acceptBtn = container.querySelector('button[data-action="accept"]') as HTMLElement;
    const rejectBtn = container.querySelector('button[data-action="reject"]') as HTMLElement;
    
    // Remove highlight and hide new text
    container.style.background = 'transparent';
    container.style.border = 'none';
    if (newTextSpan) newTextSpan.style.display = 'none';
    if (oldTextSpan) {
      oldTextSpan.style.textDecoration = 'none';
      oldTextSpan.style.color = '#000000';
    }
    
    // Remove buttons and add X
    if (acceptBtn) acceptBtn.remove();
    if (rejectBtn) rejectBtn.remove();
    const statusSpan = document.createElement('span');
    statusSpan.style.cssText = 'color: #EF4444; margin-left: 8px; font-size: 14px; font-weight: bold;';
    statusSpan.textContent = '✗ Rejected';
    container.appendChild(statusSpan);
    
    // Update state WITHOUT triggering re-render (update in-place for later use)
    const changeIndex = changes.findIndex(c => c.id === changeId);
    if (changeIndex !== -1) {
      changes[changeIndex].status = 'rejected';
    }
  };
  
  const injectChangesWithStatus = (html: string, changesList: Change[]): string => {
    let modifiedHtml = html;
    
    // Only inject pending changes (not accepted/rejected)
    const pendingChanges = changesList.filter(c => c.status === 'pending');
    const acceptedChanges = changesList.filter(c => c.status === 'accepted');
    const rejectedChanges = changesList.filter(c => c.status === 'rejected');
    
    pendingChanges.forEach((change, idx) => {
      // Same regex pattern as before
      const escapeRegex = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      
      const textChars = change.current_text.split('');
      const pattern = textChars.map((char, charIdx) => {
        if (char === ' ' || char === '\t') {
          // For whitespace: match space/nbsp, then any combo of spans/nbsp/spaces
          // This handles "For: \t" where space is in first span, then </span><span>, then 8 nbsp
          return '(?:&nbsp;|\\s| )(?:(?:</span>|<span[^>]*>|&nbsp;|\\s| )*)';
        } else if (char === '_') {
          // Underscores might be repeated (e.g., "_______")
          const escaped = escapeRegex(char);
          return `(?:</span>)?(?:<span[^>]*>)*${escaped}+(?:</span>)?(?:<span[^>]*>)*`;
        } else {
          // Regular character: allow span tags before and after
          const escaped = escapeRegex(char).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          return `(?:</span>)?(?:<span[^>]*>)*${escaped}(?:</span>)?(?:<span[^>]*>)*`;
        }
      }).join('');
      
      const regex = new RegExp(pattern, 'i');
      let match = modifiedHtml.match(regex);
      
      // FALLBACK for signature fields: If main regex fails, try simpler matching
      const isSignatureField = change.current_text.startsWith('By:') || change.current_text.startsWith('Title:') || change.current_text.startsWith('For:') || change.current_text.startsWith('Date:');
      if (!match && isSignatureField) {
        // Extract the label (e.g., "By:", "Title:") and find it in HTML
        const label = change.current_text.split(':')[0] + ':';
        const labelIndex = modifiedHtml.indexOf(label);
        
        if (labelIndex !== -1) {
          // Grab everything from label until end of paragraph
          let endIndex = modifiedHtml.indexOf('</p>', labelIndex);
          if (endIndex === -1) endIndex = labelIndex + 400;
          match = [modifiedHtml.substring(labelIndex, endIndex)];
        }
      }
      
      if (match) {
        const matchedText = match[0];
        const newTextEscaped = change.new_text
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;');
        
        const acceptBtn = `<button data-action="accept" data-change-id="${change.id}" style="display: inline-block; padding: 6px 12px; background: linear-gradient(135deg, rgba(34, 197, 94, 0.4), rgba(34, 197, 94, 0.3)); color: rgb(22, 163, 74); border: 2px solid rgb(34, 197, 94); border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: bold; margin-left: 12px; vertical-align: middle; box-shadow: 0 2px 4px rgba(34, 197, 94, 0.3); transition: all 0.2s;">✓ Accept</button>`;
        const rejectBtn = `<button data-action="reject" data-change-id="${change.id}" style="display: inline-block; padding: 6px 12px; background: linear-gradient(135deg, rgba(239, 68, 68, 0.4), rgba(239, 68, 68, 0.3)); color: rgb(220, 38, 38); border: 2px solid rgb(239, 68, 68); border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: bold; margin-left: 8px; vertical-align: middle; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3); transition: all 0.2s;">✗ Reject</button>`;
        
        const replacement = `<span class="change-container" data-change-id="${change.id}" style="background: rgba(255, 255, 0, 0.2); padding: 4px 6px; border-radius: 4px; display: inline; border: 1px dashed rgba(255, 193, 7, 0.5);">` +
          `<span class="old-text" style="text-decoration: line-through; color: #000000;">${matchedText}</span>` +
          `<span class="new-text" style="text-decoration: underline; color: #DC2626; font-weight: 600;">${newTextEscaped}</span>` +
          acceptBtn + rejectBtn +
          `</span>`;
        
        modifiedHtml = modifiedHtml.replace(matchedText, replacement);
      }
      // Skip logging for failed matches (performance optimization)
    });
    
    // Now handle accepted/rejected changes
    changesList.filter(c => c.status !== 'pending').forEach(change => {
      const escapeRegex = (str: string) => str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      
      // ALWAYS search for current_text (old text) in the original HTML
      const textChars = change.current_text.split('');
      const pattern = textChars.map((char, charIdx) => {
        if (char === ' ' || char === '\t') {
          // For whitespace: match space/nbsp, then any combo of spans/nbsp/spaces
          return '(?:&nbsp;|\\s| )(?:(?:</span>|<span[^>]*>|&nbsp;|\\s| )*)';
        } else if (char === '_') {
          // Underscores might be repeated (e.g., "_______")
          const escaped = escapeRegex(char);
          return `(?:</span>)?(?:<span[^>]*>)*${escaped}+(?:</span>)?(?:<span[^>]*>)*`;
        } else {
          // Regular character: allow span tags before and after
          const escaped = escapeRegex(char).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
          return `(?:</span>)?(?:<span[^>]*>)*${escaped}(?:</span>)?(?:<span[^>]*>)*`;
        }
      }).join('');
      
      const regex = new RegExp(pattern, 'i');
      let match = modifiedHtml.match(regex);
      
      // FALLBACK for signature fields in accepted/rejected
      if (!match && (change.current_text.startsWith('By:') || change.current_text.startsWith('Title:') || change.current_text.startsWith('For:') || change.current_text.startsWith('Date:'))) {
        const label = change.current_text.split(':')[0] + ':';
        const labelIndex = modifiedHtml.indexOf(label);
        if (labelIndex !== -1) {
          let endIndex = modifiedHtml.indexOf('</p>', labelIndex);
          if (endIndex === -1) endIndex = labelIndex + 400;
          match = [modifiedHtml.substring(labelIndex, endIndex)];
        }
      }
      
      if (match) {
        const matchedText = match[0];
        
        // Replace with appropriate text based on status
        let replacement;
        if (change.status === 'accepted') {
          // Show new text with green checkmark
          const newTextEscaped = change.new_text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;');
          const statusBadge = '<span style="color: #22C55E; margin-left: 8px; font-size: 14px; font-weight: bold;">✓ Accepted</span>';
          replacement = `<span style="color: #000000;">${newTextEscaped}</span>${statusBadge}`;
        } else {
          // Show old text with red X
          const oldTextEscaped = change.current_text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;');
          const statusBadge = '<span style="color: #EF4444; margin-left: 8px; font-size: 14px; font-weight: bold;">✗ Rejected</span>';
          replacement = `<span style="color: #000000;">${oldTextEscaped}</span>${statusBadge}`;
        }
        
        modifiedHtml = modifiedHtml.replace(matchedText, replacement);
      }
    });
    
    return modifiedHtml;
  };

  const handleAcceptAll = () => {
    setChanges((prev) => {
      const updated = prev.map((c) => ({ ...c, status: 'accepted' }));
      // For "accept all", regenerate HTML (less frequent operation, acceptable)
      if (originalHtml) {
        const newHtml = injectChangesWithStatus(originalHtml, updated);
        setDocumentHtml(newHtml);
      }
      return updated;
    });
  };

  const handleRejectAll = () => {
    setChanges((prev) => {
      const updated = prev.map((c) => ({ ...c, status: 'rejected' }));
      // For "reject all", regenerate HTML (less frequent operation, acceptable)
      if (originalHtml) {
        const newHtml = injectChangesWithStatus(originalHtml, updated);
        setDocumentHtml(newHtml);
      }
      return updated;
    });
  };

  const handleDocumentClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
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
      e.preventDefault();
      e.stopPropagation();
    }
  };

  const applyChanges = async () => {
    try {
      setApplying(true);
      setError(null);

      // Filter and send only accepted changes
      const acceptedChanges = changes.filter(c => c.status === 'accepted');
      
      const response = await fetch(`/v1/changes/apply-accepted/${documentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-ID': '1',
        },
        credentials: 'include',
        body: JSON.stringify({
          accepted_changes: acceptedChanges,
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
      <style dangerouslySetInnerHTML={{ __html: `
        .document-content * {
          color: #000000 !important;
        }
        .document-content p {
          margin-bottom: 10pt;
          line-height: 1.15;
          text-align: justify;
        }
        .document-content .change-container {
          background: rgba(255, 255, 0, 0.2);
          padding: 4px 6px;
          border-radius: 4px;
          display: inline;
          border: 1px dashed rgba(255, 193, 7, 0.6);
        }
        .document-content .change-container .old-text {
          color: #000000 !important;
          text-decoration: line-through;
        }
        .document-content .change-container .new-text {
          color: #DC2626 !important;
          text-decoration: underline;
          font-weight: 600;
        }
        .document-content button[data-action] {
          display: inline-block !important;
          padding: 6px 12px !important;
          margin-left: 8px !important;
          font-size: 13px !important;
          font-weight: bold !important;
          cursor: pointer !important;
          transition: all 0.2s ease !important;
          vertical-align: middle !important;
          border-radius: 6px !important;
        }
        .document-content button[data-action="accept"] {
          background: linear-gradient(135deg, rgba(34, 197, 94, 0.4), rgba(34, 197, 94, 0.3)) !important;
          color: rgb(22, 163, 74) !important;
          border: 2px solid rgb(34, 197, 94) !important;
          box-shadow: 0 2px 4px rgba(34, 197, 94, 0.3) !important;
        }
        .document-content button[data-action="accept"]:hover {
          background: linear-gradient(135deg, rgba(34, 197, 94, 0.6), rgba(34, 197, 94, 0.5)) !important;
          transform: scale(1.05) !important;
          box-shadow: 0 4px 8px rgba(34, 197, 94, 0.4) !important;
        }
        .document-content button[data-action="reject"] {
          background: linear-gradient(135deg, rgba(239, 68, 68, 0.4), rgba(239, 68, 68, 0.3)) !important;
          color: rgb(220, 38, 38) !important;
          border: 2px solid rgb(239, 68, 68) !important;
          box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3) !important;
        }
        .document-content button[data-action="reject"]:hover {
          background: linear-gradient(135deg, rgba(239, 68, 68, 0.6), rgba(239, 68, 68, 0.5)) !important;
          transform: scale(1.05) !important;
          box-shadow: 0 4px 8px rgba(239, 68, 68, 0.4) !important;
        }
      ` }} />
      
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
        <div className="text-xs text-yellow-400 mb-3 p-2 bg-yellow-500/10 rounded border border-yellow-500/20">
          ⚠️ Inline buttons should appear in the document above. If you don't see them, check the browser console (F12) for debugging info.
        </div>
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

