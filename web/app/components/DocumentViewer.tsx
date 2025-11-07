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
      
      console.log('📄 Document data loaded:');
      console.log('  - HTML length:', html.length);
      console.log('  - Text length:', text.length);
      console.log('  - HTML starts with:', html.substring(0, 100));
      
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
      console.log('📝 After injection, HTML length:', injectedHtml.length);
      console.log('📝 Buttons in injected HTML:', (injectedHtml.match(/data-action="accept"/g) || []).length);
      setDocumentHtml(injectedHtml);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate changes');
    } finally {
      setLoading(false);
    }
  };

  const injectChangesIntoHtml = (html: string, changesList: Change[]): string => {
    // The backend wraps each word/char in <span> tags, so we need to search across tags
    // Strategy: Create a regex pattern that matches the text even when split across spans
    let modifiedHtml = html;
    
    console.log('🔧 Injecting', changesList.length, 'changes into HTML');
    
    changesList.forEach((change, idx) => {
      console.log(`📝 Change ${idx + 1}: "${change.current_text.substring(0, 30)}..." → "${change.new_text.substring(0, 30)}..."`);
      
      // Escape special regex characters in the search text
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
      const match = modifiedHtml.match(regex);
      
      console.log(`   ${match ? '✅' : '❌'} Text found in HTML:`, !!match);
      
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
        console.log(`   ✅ Buttons injected for change ${idx + 1}`);
      } else {
        console.log(`   ⚠️ Could not inject buttons for change ${idx + 1}`);
      }
    });
    
    const buttonCount = (modifiedHtml.match(/data-action="accept"/g) || []).length;
    console.log(`✅ Injection complete. Total accept buttons in HTML: ${buttonCount}`);
    
    if (buttonCount === 0 && changesList.length > 0) {
      console.error('⚠️ WARNING: No buttons were injected! Text matching may have failed.');
      console.log('Sample HTML (first 500 chars):', modifiedHtml.substring(0, 500));
      console.log('Sample change 1 - Raw text:', changesList[0]?.current_text);
      console.log('Sample change 1 - Escaped text:', changesList[0]?.current_text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;'));
      console.log('HTML contains "September":', modifiedHtml.includes('September'));
      console.log('HTML contains "Dear":', modifiedHtml.includes('Dear'));
      console.log('HTML contains "NAME":', modifiedHtml.includes('NAME'));
    }
    
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
    console.log(`✅ handleAccept called for change ${changeId}`);
    setChanges((prev) => {
      const updated = prev.map((c) =>
        c.id === changeId ? { ...c, status: 'accepted' } : c
      );
      // Regenerate HTML with updated changes
      regenerateHtmlWithChanges(updated);
      return updated;
    });
  };

  const handleReject = (changeId: string) => {
    console.log(`❌ handleReject called for change ${changeId}`);
    setChanges((prev) => {
      const updated = prev.map((c) =>
        c.id === changeId ? { ...c, status: 'rejected' } : c
      );
      // Regenerate HTML with updated changes
      regenerateHtmlWithChanges(updated);
      return updated;
    });
  };
  
  const regenerateHtmlWithChanges = (updatedChanges: Change[]) => {
    console.log('🔄 Regenerating HTML with updated changes');
    console.log(`   Using cached original HTML (${originalHtml.length} chars)`);
    
    // Use cached original HTML for instant regeneration
    if (originalHtml) {
      const newHtml = injectChangesWithStatus(originalHtml, updatedChanges);
      setDocumentHtml(newHtml);
      console.log('✅ HTML regenerated instantly from cache');
    } else {
      console.error('⚠️ Original HTML not cached, cannot regenerate');
    }
  };
  
  const injectChangesWithStatus = (html: string, changesList: Change[]): string => {
    let modifiedHtml = html;
    
    // Only inject pending changes (not accepted/rejected)
    const pendingChanges = changesList.filter(c => c.status === 'pending');
    const acceptedChanges = changesList.filter(c => c.status === 'accepted');
    const rejectedChanges = changesList.filter(c => c.status === 'rejected');
    
    console.log(`🔧 Injecting changes: ${pendingChanges.length} pending, ${acceptedChanges.length} accepted, ${rejectedChanges.length} rejected`);
    
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
      const match = modifiedHtml.match(regex);
      
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
      } else {
        // Debug: Show what we're looking for vs what's in the HTML
        console.log(`   🔍 FAILED TO MATCH: "${change.current_text.substring(0, 50)}"`);
        console.log(`      Pattern: ${pattern.substring(0, 200)}...`);
        
        // Debug signature block fields
        if (change.current_text.includes('By:')) {
          const byIndex = modifiedHtml.indexOf('By:');
          if (byIndex !== -1) {
            console.log(`      Found "By:" in HTML at index ${byIndex}`);
            console.log(`      HTML: "${modifiedHtml.substring(byIndex, byIndex + 350)}"`);
          }
        }
        if (change.current_text.includes('Title:')) {
          const titleIndex = modifiedHtml.indexOf('Title:');
          if (titleIndex !== -1) {
            console.log(`      Found "Title:" in HTML at index ${titleIndex}`);
            console.log(`      HTML: "${modifiedHtml.substring(titleIndex, titleIndex + 350)}"`);
          }
        }
        if (change.current_text.includes('For:')) {
          const forIndex = modifiedHtml.indexOf('For:');
          if (forIndex !== -1) {
            console.log(`      Found "For:" in HTML at index ${forIndex}`);
            console.log(`      HTML: "${modifiedHtml.substring(forIndex, forIndex + 350)}"`);
          }
        }
        if (change.current_text.includes('Date:')) {
          const dateIndex = modifiedHtml.indexOf('Date:');
          if (dateIndex !== -1) {
            console.log(`      Found "Date:" in HTML at index ${dateIndex}`);
            console.log(`      HTML: "${modifiedHtml.substring(dateIndex, dateIndex + 350)}"`);
          }
        }
        
        if (change.current_text.includes('five')) {
          const fiveIndex = modifiedHtml.toLowerCase().indexOf('five');
          if (fiveIndex !== -1) {
            console.log(`      Found "five" in HTML at index ${fiveIndex}`);
            console.log(`      HTML: "${modifiedHtml.substring(fiveIndex, fiveIndex + 250)}"`);
          } else {
            console.log(`      "five" not found in HTML - checking for "5"`);
            const numIndex = modifiedHtml.indexOf('5');
            if (numIndex !== -1) {
              console.log(`      Found "5" at index ${numIndex}`);
              console.log(`      HTML: "${modifiedHtml.substring(numIndex, numIndex + 250)}"`);
            }
          }
        }
      }
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
      const match = modifiedHtml.match(regex);
      
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
        console.log(`   ✅ ${change.status === 'accepted' ? 'Accepted' : 'Rejected'} change displayed`);
      } else {
        console.log(`   ⚠️ Could not find text for ${change.status} change: "${change.current_text.substring(0, 40)}..."`);
      }
    });
    
    return modifiedHtml;
  };

  const handleAcceptAll = () => {
    const updated = changes.map((c) => ({ ...c, status: 'accepted' }));
    setChanges(updated);
    regenerateHtmlWithChanges(updated);
  };

  const handleRejectAll = () => {
    const updated = changes.map((c) => ({ ...c, status: 'rejected' }));
    setChanges(updated);
    regenerateHtmlWithChanges(updated);
  };

  const updateVisualDisplay = (changeId: string, status: 'accepted' | 'rejected') => {
    console.log(`🎨 Updating visual display for change ${changeId} as ${status}`);
    
    // Give React a chance to render first
    setTimeout(() => {
      // Find the change container in the DOM
      const container = document.querySelector(`.change-container[data-change-id="${changeId}"]`) as HTMLElement;
      if (!container) {
        console.log(`   ❌ Container not found for change ${changeId}`);
        return;
      }
      
      console.log(`   ✅ Found container for change ${changeId}`);
      
      const oldTextSpan = container.querySelector('.old-text') as HTMLElement;
      const newTextSpan = container.querySelector('.new-text') as HTMLElement;
      const acceptBtn = container.querySelector('button[data-action="accept"]') as HTMLElement;
      const rejectBtn = container.querySelector('button[data-action="reject"]') as HTMLElement;
      
      // Add transition for smooth animation
      if (container) {
        container.style.transition = 'all 0.3s ease';
      }
      if (oldTextSpan) {
        oldTextSpan.style.transition = 'all 0.3s ease';
      }
      if (newTextSpan) {
        newTextSpan.style.transition = 'all 0.3s ease';
      }
      
      // Remove yellow highlight background with animation
      container.style.background = 'transparent';
      container.style.border = 'none';
      
      if (status === 'accepted') {
        console.log(`   ✅ Accepting change - hiding old text, showing new text as normal`);
        // Hide old text, show new text as normal (accepted)
        if (oldTextSpan) {
          oldTextSpan.style.opacity = '0';
          setTimeout(() => {
            oldTextSpan.style.display = 'none';
          }, 300);
        }
        if (newTextSpan) {
          newTextSpan.style.textDecoration = 'none';
          newTextSpan.style.color = '#000000';
          newTextSpan.style.fontWeight = 'normal';
        }
        // Replace buttons with green checkmark
        if (acceptBtn) {
          acceptBtn.style.opacity = '0';
          setTimeout(() => acceptBtn.remove(), 300);
        }
        if (rejectBtn) {
          rejectBtn.style.opacity = '0';
          setTimeout(() => rejectBtn.remove(), 300);
        }
        
        // Add status indicator
        const statusSpan = document.createElement('span');
        statusSpan.style.cssText = 'color: #22C55E; margin-left: 12px; font-size: 14px; font-weight: bold; animation: fadeIn 0.3s ease;';
        statusSpan.textContent = '✓ Accepted';
        container.appendChild(statusSpan);
        
      } else if (status === 'rejected') {
        console.log(`   ❌ Rejecting change - hiding new text, showing old text as normal`);
        // Hide new text, show old text as normal (rejected)
        if (newTextSpan) {
          newTextSpan.style.opacity = '0';
          setTimeout(() => {
            newTextSpan.style.display = 'none';
          }, 300);
        }
        if (oldTextSpan) {
          oldTextSpan.style.textDecoration = 'none';
          oldTextSpan.style.color = '#000000';
        }
        // Replace buttons with red X
        if (acceptBtn) {
          acceptBtn.style.opacity = '0';
          setTimeout(() => acceptBtn.remove(), 300);
        }
        if (rejectBtn) {
          rejectBtn.style.opacity = '0';
          setTimeout(() => rejectBtn.remove(), 300);
        }
        
        // Add status indicator
        const statusSpan = document.createElement('span');
        statusSpan.style.cssText = 'color: #EF4444; margin-left: 12px; font-size: 14px; font-weight: bold; animation: fadeIn 0.3s ease;';
        statusSpan.textContent = '✗ Rejected';
        container.appendChild(statusSpan);
      }
      
      console.log(`   ✅ Visual update complete for change ${changeId}`);
    }, 50); // Small delay to ensure DOM is ready
  };

  const handleDocumentClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    
    console.log('🖱️ Document clicked:', target.tagName, target.getAttribute('data-action'));
    
    // Check if clicked on accept/reject button
    const button = target.closest('[data-action]');
    if (button) {
      const action = button.getAttribute('data-action');
      const changeId = button.getAttribute('data-change-id');
      
      console.log(`🎯 Button clicked: action=${action}, changeId=${changeId}`);
      
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
      
      console.log(`📤 Sending ${acceptedChanges.length} accepted changes to backend`);
      acceptedChanges.forEach((c, idx) => {
        console.log(`   ${idx + 1}. ${c.current_text.substring(0, 40)} → ${c.new_text.substring(0, 40)}`);
      });
      
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

