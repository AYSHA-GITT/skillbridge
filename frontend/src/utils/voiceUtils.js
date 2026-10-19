/**
 * Voice utilities for SkillBridge.
 * Uses the Web Speech API (SpeechRecognition for STT, SpeechSynthesis for TTS).
 * Operates strictly with user-initiated actions, never recording continuously.
 */

export function isSpeechRecognitionSupported() {
  return typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);
}

export function isSpeechSynthesisSupported() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window;
}

/**
 * Sanitizes speech transcript by removing immediate consecutive repeated words
 * and normalizing whitespace.
 * @param {string} text - Raw speech transcript.
 * @returns {string} Cleaned transcript.
 */
export function cleanSpeechTranscript(text) {
  if (!text) return '';
  return text
    .replace(/\b(\w+)(?:\s+\1\b)+/gi, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Starts user-initiated speech recognition.
 * @param {Function} onTranscript - Callback with transcribed string.
 * @param {Function} onError - Callback on error.
 * @param {Function} onEnd - Callback when recording terminates.
 * @returns {Object} SpeechRecognition instance with stop() control.
 */
export function startSpeechRecognition(onTranscript, onError, onEnd) {
  if (!isSpeechRecognitionSupported()) {
    if (onError) onError('Speech recognition is not supported in this browser.');
    return null;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();

  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    let finalPart = '';
    let interimPart = '';
    for (let i = 0; i < event.results.length; ++i) {
      const piece = event.results[i][0]?.transcript || '';
      if (event.results[i].isFinal) {
        finalPart += piece + ' ';
      } else {
        interimPart += piece;
      }
    }
    const current = cleanSpeechTranscript(finalPart + ' ' + interimPart);
    if (onTranscript && current) onTranscript(current);
  };

  recognition.onerror = (event) => {
    if (event.error === 'no-speech') {
      // Harmless silence pause, do not show blocking error
      return;
    }
    let errMessage = 'Microphone access failed or voice was not detected.';
    if (event.error === 'not-allowed') {
      errMessage = 'Microphone permission denied. Please allow microphone access in your browser settings.';
    }
    if (onError) onError(errMessage);
  };

  recognition.onend = () => {
    if (onEnd) onEnd();
  };

  try {
    recognition.start();
    return recognition;
  } catch (err) {
    if (onError) onError('Could not initialize microphone: ' + err.message);
    return null;
  }
}

/**
 * Speaks text using browser SpeechSynthesis with clean paragraph parsing.
 * @param {string} text - Content to speak.
 * @param {Function} onStart - Callback on speech begin.
 * @param {Function} onEnd - Callback on speech end.
 */
export function speakText(text, onStart, onEnd) {
  if (!isSpeechSynthesisSupported()) return;

  // Stop any active speech first
  stopSpeaking();

  // Strip markdown formatting before reading
  const clean = text
    .replace(/\[Source\s*\d+[^\]]*\]/gi, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/#{1,6}\s+/g, '')
    .replace(/`{1,3}[^`]*`{1,3}/g, '')
    .replace(/•/g, '')
    .replace(/\n+/g, ' ')
    .trim();

  if (!clean) return;

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.lang = 'en-US';
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  if (onStart) utterance.onstart = onStart;
  if (onEnd) utterance.onend = onEnd;
  utterance.onerror = () => {
    if (onEnd) onEnd();
  };

  window.speechSynthesis.speak(utterance);
}

export function stopSpeaking() {
  if (isSpeechSynthesisSupported()) {
    window.speechSynthesis.cancel();
  }
}

export function isSpeaking() {
  return isSpeechSynthesisSupported() && window.speechSynthesis.speaking;
}
