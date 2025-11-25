'use client';

import { useState, useEffect, useRef } from 'react';
import { CheckCircle, XCircle, Download, Loader, FileSignature, ArrowLeft, ShieldCheck, ChevronRight } from 'lucide-react';

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
  signatureFile?: File | null;
}

// Helper function to convert File to data URL
const fileToDataUrl = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};

export default function DocumentViewer({ documentId, documentText, onComplete, firmDetails, customRules, signatureFile }: DocumentViewerProps) {
  const [changes, setChanges] = useState<Change[]>([]);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documentHtml, setDocumentHtml] = useState<string>('');
  const [originalHtml, setOriginalHtml] = useState<string>(''); // Cache original HTML
  const [signatureDataUrl, setSignatureDataUrl] = useState<string | null>(null);
  const [documentSegments, setDocumentSegments] = useState<any[]>([]);
  const [activeChangeId, setActiveChangeId] = useState<string | null>(null);
  const documentRef = useRef<HTMLDivElement | null>(null);
  const changeRefs = useRef<Record<string, HTMLElement>>({});

  // Generate changes when component mounts
  useEffect(() => {
    loadDocumentAndGenerateChanges();
  }, []);
  
  // Convert signature file to data URL for preview
  useEffect(() => {
    if (signatureFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setSignatureDataUrl(e.target?.result as string);
      };
      reader.readAsDataURL(signatureFile);
    } else {
      setSignatureDataUrl(null);
    }
  }, [signatureFile]);
  
  // Update document HTML when signature changes
  useEffect(() => {
    if (originalHtml && signatureDataUrl) {
      // Regenerate HTML with current changes and signature
      let html = injectChangesIntoHtml(originalHtml, changes);
      html = injectSignaturePreview(html, signatureDataUrl);
      setDocumentHtml(html);
    }
  }, [signatureDataUrl]);

  // Capture references to each inline change container for DocuSign-style navigation
  useEffect(() => {
    if (!documentRef.current) return;
    const containers = documentRef.current.querySelectorAll<HTMLElement>('.change-container');
    const map: Record<string, HTMLElement> = {};
    containers.forEach((node) => {
      const id = node.getAttribute('data-change-id');
      if (id) {
        map[id] = node;
      }
    });
    changeRefs.current = map;
  }, [documentHtml, changes]);

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
      if (!html) {
        buildDocumentSegments(text, generatedChanges);
      }
      let injectedHtml = injectChangesIntoHtml(html, generatedChanges);
      
      // Inject signature preview if available (check both state and prop)
      const currentSignatureUrl = signatureDataUrl || (signatureFile ? await fileToDataUrl(signatureFile) : null);
      if (currentSignatureUrl) {
        injectedHtml = injectSignaturePreview(injectedHtml, currentSignatureUrl);
        if (!signatureDataUrl) {
          setSignatureDataUrl(currentSignatureUrl);
        }
      }
      
      // Changes injected into HTML
      setDocumentHtml(injectedHtml);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate changes');
    } finally {
      setLoading(false);
    }
  };

  const injectSignaturePreview = (html: string, signatureDataUrl: string): string => {
    const signatureHtml = `<img src="${signatureDataUrl}" alt="Signature" style="max-width: 300px; max-height: 150px; border: 1px solid #ccc; padding: 5px; background: white; display: inline-block; vertical-align: middle; margin-left: 10px;" />`;
    
    // Find "Signed:" paragraph - match the full paragraph including nested tags
    const signedPattern = /<p([^>]*)>(?:(?!<\/p>).)*?Signed:(?:(?!<\/p>).)*?<\/p>/is;
    let match = html.match(signedPattern);
    
    if (match) {
      const fullParagraph = match[0];
      // Replace underscores with strikethrough, then insert signature after the last underscore
      // Find the last underscore position in the HTML
      const lastUnderscoreIndex = fullParagraph.lastIndexOf('_');
      
      if (lastUnderscoreIndex !== -1) {
        // Find the end of the underscore sequence
        let underscoreEnd = lastUnderscoreIndex + 1;
        while (underscoreEnd < fullParagraph.length && fullParagraph[underscoreEnd] === '_') {
          underscoreEnd++;
        }
        
        // Split: before underscores, underscores, after underscores
        const beforeUnderscores = fullParagraph.substring(0, lastUnderscoreIndex);
        const underscores = fullParagraph.substring(lastUnderscoreIndex, underscoreEnd);
        const afterUnderscores = fullParagraph.substring(underscoreEnd);
        
        // Apply strikethrough to underscores and insert signature
        const replacement = beforeUnderscores + 
          `<span style="text-decoration: line-through;">${underscores}</span>` + 
          signatureHtml + 
          afterUnderscores;
        
        return html.replace(signedPattern, replacement);
      }
    }
    
    // Fallback: Look for "By:" with underscores
    const byPattern = /<p([^>]*)>(?:(?!<\/p>).)*?By:(?:(?!<\/p>).)*?_(?:(?!<\/p>).)*?<\/p>/is;
    let byMatch = html.match(byPattern);
    
    if (byMatch) {
      const fullParagraph = byMatch[0];
      const lastUnderscoreIndex = fullParagraph.lastIndexOf('_');
      
      if (lastUnderscoreIndex !== -1) {
        let underscoreEnd = lastUnderscoreIndex + 1;
        while (underscoreEnd < fullParagraph.length && fullParagraph[underscoreEnd] === '_') {
          underscoreEnd++;
        }
        
        const beforeUnderscores = fullParagraph.substring(0, lastUnderscoreIndex);
        const underscores = fullParagraph.substring(lastUnderscoreIndex, underscoreEnd);
        const afterUnderscores = fullParagraph.substring(underscoreEnd);
        
        const replacement = beforeUnderscores + 
          `<span style="text-decoration: line-through;">${underscores}</span>` + 
          signatureHtml + 
          afterUnderscores;
        
        return html.replace(byPattern, replacement);
      }
    }
    
    return html;
  };

  const injectChangesIntoHtml = (html: string, changesList: Change[]): string => {
    let modifiedHtml = html;
    
    changesList.forEach((change, idx) => {
      let match = null;
      
      // OPTIMIZED: Use simple string matching instead of complex regex
      // Check if it's a signature field first (these are easiest)
      const isSignatureField = change.current_text.startsWith('By:') || 
                               change.current_text.startsWith('Title:') || 
                               change.current_text.startsWith('For:') || 
                               change.current_text.startsWith('Date:');
      
      if (isSignatureField) {
        // For signature fields, just find the label and grab the paragraph
        const label = change.current_text.split(':')[0] + ':';
        const labelIndex = modifiedHtml.indexOf(label);
        if (labelIndex !== -1) {
          let endIndex = modifiedHtml.indexOf('</p>', labelIndex);
          if (endIndex === -1) endIndex = labelIndex + 400;
          match = [modifiedHtml.substring(labelIndex, endIndex)];
        }
      } else {
        // For other text, use simple indexOf with some context checking
        // Remove extra whitespace for matching
        const searchText = change.current_text.trim();
        const startIdx = modifiedHtml.indexOf(searchText);
        
        if (startIdx !== -1) {
          // Found exact text - use it
          match = [searchText];
        } else {
          // Try finding just the first few words
          const firstWords = searchText.split(/\s+/).slice(0, 3).join(' ');
          const idx = modifiedHtml.indexOf(firstWords);
          if (idx !== -1) {
            // Found beginning, grab a chunk
            let endIdx = modifiedHtml.indexOf('</span>', idx + firstWords.length);
            if (endIdx === -1) endIdx = idx + change.current_text.length * 3;
            match = [modifiedHtml.substring(idx, endIdx)];
          }
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
        const acceptBtn = `<button data-action="accept" data-change-id="${change.id}">✓ Accept</button>`;
        const rejectBtn = `<button data-action="reject" data-change-id="${change.id}">✗ Reject</button>`;
        
        const replacement = `<span class="change-container" data-change-id="${change.id}">` +
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
    container.classList.add('docu-tag-complete');
    container.classList.remove('docu-tag-rejected');
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
    statusSpan.className = 'docu-status docu-status--accepted';
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
    container.classList.add('docu-tag-rejected');
    container.classList.remove('docu-tag-complete');
    if (newTextSpan) newTextSpan.style.display = 'none';
    if (oldTextSpan) {
      oldTextSpan.style.textDecoration = 'none';
      oldTextSpan.style.color = '#000000';
    }
    
    // Remove buttons and add X
    if (acceptBtn) acceptBtn.remove();
    if (rejectBtn) rejectBtn.remove();
    const statusSpan = document.createElement('span');
    statusSpan.className = 'docu-status docu-status--rejected';
    statusSpan.textContent = '✗ Rejected';
    container.appendChild(statusSpan);
    
    // Update state WITHOUT triggering re-render (update in-place for later use)
    const changeIndex = changes.findIndex(c => c.id === changeId);
    if (changeIndex !== -1) {
      changes[changeIndex].status = 'rejected';
    }
  };

  const scrollToChange = (changeId: string) => {
    const node = changeRefs.current[changeId];
    if (!node) return;
    
    setActiveChangeId(changeId);
    node.scrollIntoView({ behavior: 'smooth', block: 'center' });
    node.classList.add('docu-highlight');
    setTimeout(() => node.classList.remove('docu-highlight'), 1500);
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
        
        const acceptBtn = `<button data-action="accept" data-change-id="${change.id}">✓ Accept</button>`;
        const rejectBtn = `<button data-action="reject" data-change-id="${change.id}">✗ Reject</button>`;
        
        const replacement = `<span class="change-container" data-change-id="${change.id}">` +
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
      
      // Use FormData to send both changes and signature file
      const formData = new FormData();
      formData.append('accepted_changes', JSON.stringify(acceptedChanges));
      
      // Add signature file if provided
      if (signatureFile) {
        formData.append('signature', signatureFile);
      }
      
      const response = await fetch(`/v1/changes/apply-accepted/${documentId}`, {
        method: 'POST',
        headers: {
          'X-User-ID': '1',
          // Don't set Content-Type - let browser set it with boundary for FormData
        },
        credentials: 'include',
        body: formData,
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
  const totalChanges = changes.length;
  const completedCount = acceptedCount + rejectedCount;
  const completionPercent = totalChanges ? Math.round((completedCount / totalChanges) * 100) : 0;

  return (
    <div className="flex flex-col gap-6">
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
          position: relative;
          display: inline-flex;
          flex-direction: column;
          gap: 6px;
          background: #EEF2FF;
          padding: 10px 12px;
          border-radius: 12px;
          border: 2px solid #4338CA;
          box-shadow: 0 8px 20px rgba(67, 56, 202, 0.15);
          margin: 4px 0;
          min-width: 180px;
        }
        .document-content .change-container::after {
          content: '';
          position: absolute;
          left: 24px;
          bottom: -10px;
          width: 14px;
          height: 14px;
          background: #EEF2FF;
          border-left: 2px solid #4338CA;
          border-bottom: 2px solid #4338CA;
          transform: rotate(45deg);
        }
        .document-content .change-container .old-text {
          color: #1F2937 !important;
          text-decoration: line-through;
          font-size: 12px;
        }
        .document-content .change-container .new-text {
          color: #111827 !important;
          text-decoration: underline;
          font-weight: 600;
        }
        .document-content .change-container.docu-tag-complete {
          background: #ECFDF5;
          border-color: #16A34A;
        }
        .document-content .change-container.docu-tag-complete::after {
          background: #ECFDF5;
          border-color: #16A34A;
        }
        .document-content .change-container.docu-tag-rejected {
          background: #FEF2F2;
          border-color: #EF4444;
        }
        .document-content .change-container.docu-tag-rejected::after {
          background: #FEF2F2;
          border-color: #EF4444;
        }
        .document-content button[data-action] {
          display: block !important;
          width: 100% !important;
          padding: 6px 0 !important;
          font-size: 12px !important;
          font-weight: 600 !important;
          border-radius: 8px !important;
          border: none !important;
          cursor: pointer !important;
          transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }
        .document-content button[data-action="accept"] {
          background: #16A34A !important;
          color: #fff !important;
          box-shadow: 0 4px 12px rgba(22, 163, 74, 0.25) !important;
        }
        .document-content button[data-action="reject"] {
          background: #EF4444 !important;
          color: #fff !important;
          box-shadow: 0 4px 12px rgba(239, 68, 68, 0.25) !important;
        }
        .document-content .docu-highlight {
          outline: 3px solid #F59E0B;
          transition: outline 0.3s ease;
        }
        .document-content .docu-status {
          font-size: 12px;
          font-weight: 600;
        }
        .document-content .docu-status--accepted {
          color: #15803D;
        }
        .document-content .docu-status--rejected {
          color: #B91C1C;
        }
      ` }} />
      
      {/* DocuSign-style header */}
      <div className="bg-[#0F172A] text-white rounded-2xl shadow-2xl px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => onComplete({ success: false })}
            className="flex items-center gap-2 text-sm text-blue-200 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Exit Review
          </button>
          <div className="flex items-center gap-3">
            <div className="bg-white/10 p-3 rounded-xl">
              <FileSignature className="w-6 h-6 text-blue-300" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-wider text-blue-300">DocuSign-Style Review</p>
              <h2 className="text-2xl font-semibold">Confidentiality Agreement</h2>
              <p className="text-sm text-blue-200">{pendingCount} actions remaining</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-sm text-blue-100 bg-white/10 px-3 py-2 rounded-xl">
            <ShieldCheck className="w-4 h-4 text-green-300" />
            <span>{completionPercent}% Complete</span>
          </div>
          <button
            onClick={handleAcceptAll}
            className="px-3 py-2 bg-white/10 text-white rounded-xl text-sm hover:bg-white/20 transition"
          >
            Accept All
          </button>
          <button
            onClick={handleRejectAll}
            className="px-3 py-2 bg-white/10 text-white rounded-xl text-sm hover:bg-white/20 transition"
          >
            Reject All
          </button>
          <button
            onClick={applyChanges}
            disabled={applying}
            className="px-5 py-2 bg-blue-500 text-white rounded-xl text-sm font-semibold hover:bg-blue-400 transition flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {applying ? (
              <>
                <Loader className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                Finish & Download
              </>
            )}
          </button>
        </div>
      </div>
      
      {/* DocuSign layout */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar */}
        <aside className="lg:w-80 bg-white rounded-2xl shadow-xl p-5 space-y-4 h-[calc(100vh-260px)] overflow-y-auto">
          <div>
            <p className="text-xs uppercase tracking-widest text-slate-400 mb-1">Guided Review</p>
            <h3 className="text-xl font-semibold text-slate-800">Required Actions</h3>
            <p className="text-sm text-slate-500 mb-3">Click any card to jump to its location in the document.</p>
            <button
              onClick={() => {
                const nextPending = changes.find(c => c.status === 'pending');
                if (nextPending) {
                  scrollToChange(nextPending.id);
                }
              }}
              className="w-full flex items-center justify-between bg-blue-50 border border-blue-200 text-blue-600 rounded-xl px-4 py-2 text-sm font-medium hover:bg-blue-100 transition"
            >
              Next pending change
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          
          <div className="space-y-3">
            {changes.map((change, idx) => {
              const isActive = activeChangeId === change.id;
              const statusColor =
                change.status === 'accepted'
                  ? 'bg-green-100 text-green-700 border-green-200'
                  : change.status === 'rejected'
                  ? 'bg-red-100 text-red-700 border-red-200'
                  : 'bg-amber-100 text-amber-700 border-amber-200';
              
              const statusLabel =
                change.status === 'accepted' ? 'Accepted' :
                change.status === 'rejected' ? 'Rejected' : 'Pending';
              
              return (
                <button
                  key={change.id}
                  onClick={() => scrollToChange(change.id)}
                  className={`w-full text-left border rounded-2xl p-4 shadow-sm hover:shadow-md transition ${
                    isActive ? 'border-blue-400 shadow-lg' : 'border-slate-100'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs uppercase tracking-widest text-slate-400 mb-2">
                    <span>Change {idx + 1}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusColor}`}>
                      {statusLabel}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-slate-800 mb-1">
                    {change.section || 'General'}
                  </h4>
                  <p className="text-xs text-slate-500 line-clamp-2">
                    {change.reason || change.current_text}
                  </p>
                </button>
              );
            })}
          </div>
        </aside>
        
        {/* Document Viewer */}
        <div className="flex-1">
          <div className="bg-[#F3F4F6] rounded-3xl shadow-inner p-6">
            <div className="flex items-center justify-between mb-4 text-sm text-slate-500">
              <div>
                Page <span className="font-semibold text-slate-700">1</span> of{' '}
                <span className="font-semibold text-slate-700">1</span>
              </div>
              <div className="flex items-center gap-2">
                <button className="px-3 py-1 rounded-full bg-white shadow text-slate-600 text-xs">-</button>
                <span className="text-xs font-semibold text-slate-700">100%</span>
                <button className="px-3 py-1 rounded-full bg-white shadow text-slate-600 text-xs">+</button>
              </div>
            </div>
            
            <div className="flex justify-center">
              <div
                className="bg-white shadow-2xl rounded-xl px-10 py-12 w-full max-w-4xl"
                style={{
                  fontFamily: 'Times New Roman, serif',
                  fontSize: '12pt',
                  lineHeight: '1.6',
                  color: '#000000',
                  minHeight: '70vh'
                }}
              >
                <div
                  ref={documentRef}
                  dangerouslySetInnerHTML={{ __html: documentHtml }}
                  onClick={handleDocumentClick}
                  style={{ color: '#000000' }}
                  className="document-content"
                />
                
                {!documentHtml && (
                  <div>
                    {documentSegments.map((para, paraIdx) => {
                      if (para.type === 'paragraph') {
                        if (para.isEmpty) {
                          return <div key={paraIdx} style={{ height: '1em' }} />;
                        }
                        
                        return (
                          <p
                            key={paraIdx}
                            className="text-black"
                            style={{
                              marginBottom: '0.75em',
                              textIndent: para.segments[0]?.content?.startsWith('\\t') ? '2em' : '0',
                              whiteSpace: 'pre-wrap',
                            }}
                          >
                            {para.segments.map((segment: any, segIdx: number) => {
                              if (segment.type === 'text') {
                                return <span key={segIdx}>{segment.content}</span>;
                              } else if (segment.type === 'change') {
                                const change = segment.change;
                                const isAccepted = change.status === 'accepted';
                                const isRejected = change.status === 'rejected';
                                
                                return (
                                  <span key={segIdx} className="inline-block">
                                    <span
                                      className="text-black"
                                      style={{
                                        textDecoration: 'line-through',
                                        display: isAccepted ? 'none' : 'inline',
                                      }}
                                    >
                                      {change.current_text}
                                    </span>
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

