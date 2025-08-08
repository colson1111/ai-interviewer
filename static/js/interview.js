/**
 * Interview chat functionality with WebSocket support
 */

class InterviewChat {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.ws = null;
        this.isConnected = false;
        this.messageQueue = [];
        
        // DOM elements
        this.chatMessages = document.getElementById('chat-messages');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.micButton = document.getElementById('mic-button');
        this.speechStatus = document.getElementById('speech-status');
        this.connectionStatus = document.getElementById('connection-status');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.toolIndicators = document.getElementById('tool-indicators');
        
        // Speech recognition
        this.recognition = null;
        this.isListening = false;
        this.speechSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
        this.accumulatedTranscript = ''; // Track accumulated speech across sessions
        
        // Audio recording for Whisper
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.whisperButton = document.getElementById('whisper-button');
        
        // Voice synthesis properties
        this.voiceEnabled = true;
        this.voiceSpeed = 1.0;
        this.currentSpeech = null;
        this.speechSynth = window.speechSynthesis;
        this.availableVoices = [];
        this.openaiTtsAvailable = false;
        this.voiceToggle = document.getElementById('voice-enabled');
        this.voiceSpeedSlider = document.getElementById('voice-speed');
        this.speedValueDisplay = document.getElementById('speed-value');
        
        // TTS (OpenAI) properties
        this.ttsEnabled = true; // Default to enabled, will be set from session
        this.ttsToggle = document.getElementById('tts-enabled');
        
        this.init();
    }
    
    init() {
        this.setupWebSocket();
        this.setupEventListeners();
        this.setupKeyboardShortcuts();
        this.setupSpeechRecognition();
        this.setupAudioRecording();
        this.setupVoiceSynthesis();
        this.setupCodeEditor();
    }
    
    setupWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${this.sessionId}`;
        
        console.log('Connecting to WebSocket:', wsUrl);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.updateConnectionStatus('Connected', 'connected');
            this.enableInput();
            
            // Send any queued messages
            while (this.messageQueue.length > 0) {
                const message = this.messageQueue.shift();
                this.ws.send(JSON.stringify(message));
            }
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            InterviewApp.showNotification('Connection error occurred', 'error');
        };
        
        this.ws.onclose = (event) => {
            console.log('WebSocket closed:', event.code, event.reason);
            this.isConnected = false;
            this.updateConnectionStatus('Disconnected', 'disconnected');
            this.disableInput();
            
            // Check if it's a 403/authentication error (likely invalid session after server restart)
            if (event.code === 1002 || event.code === 1006) { // 1002 = protocol error, 1006 = abnormal closure
                console.log('Session likely invalid after server restart. Redirecting to home...');
                setTimeout(() => {
                    alert('Server restarted. Redirecting to start a new interview session...');
                    window.location.href = '/';
                }, 2000);
                return;
            }
            
            // For other errors, attempt to reconnect after delay
            if (event.code !== 1000) { // Not a normal closure
                setTimeout(() => {
                    if (!this.isConnected) {
                        console.log('Attempting to reconnect...');
                        this.setupWebSocket();
                    }
                }, 3000);
            }
        };
    }
    
    setupEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => {
            this.sendMessage();
        });
        
        // Message input enter key
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => {
            this.messageInput.style.height = 'auto';
            this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
        });
        
        // End interview button
        const endButton = document.getElementById('end-interview');
        if (endButton) {
            endButton.addEventListener('click', () => {
                this.endInterview();
            });
        }
        
        // Microphone button
        if (this.micButton) {
            this.micButton.addEventListener('click', () => {
                this.toggleSpeechRecognition();
            });
        }
        
        // Whisper button
        if (this.whisperButton) {
            this.whisperButton.addEventListener('click', () => {
                this.transcribeWithWhisper();
            });
        }
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter to send message
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
            
            // Escape to focus input
            if (e.key === 'Escape') {
                this.messageInput.focus();
            }
        });
    }
    
    sendMessage() {
        const content = this.messageInput.value.trim();
        if (!content || !this.isConnected) return;
        
        const message = {
            type: 'user_message',
            content: content,
            timestamp: new Date().toISOString()
        };
        
        // Add to UI immediately
        this.addMessageToChat('user', content);
        
        // Send via WebSocket
        if (this.isConnected) {
            this.ws.send(JSON.stringify(message));
        } else {
            this.messageQueue.push(message);
        }
        
        // Clear input
        this.messageInput.value = '';
        this.accumulatedTranscript = ''; // Reset speech transcript for next message
        this.messageInput.style.height = 'auto';
        this.disableInput();
    }
    
    handleMessage(data) {
        console.log('Received message:', data);
        
        switch (data.type) {
            case 'interviewer':
                this.addMessageToChat('interviewer', data.content, data.timestamp);
                this.enableInput();
                this.hideTypingIndicator();
                
                // Speak the interviewer's message
                this.speakText(data.content);
                break;
                
            case 'tool_indicator':
                this.showToolActivity(data.tool, data.status);
                break;
                
            case 'typing':
                this.showTypingIndicator();
                break;
                
            case 'cost_update':
                console.log('Received cost update:', data);
                console.log('Cost data content:', data.content);
                console.log('Cost data type:', typeof data.content);
                if (data.content && typeof data.content === 'object') {
                    this.updateCostDisplay(data.content);
                } else {
                    console.warn('Invalid cost data received:', data.content);
                }
                break;
                
            case 'error':
                this.addMessageToChat('error', data.content, data.timestamp);
                this.enableInput();
                InterviewApp.showNotification('Interview error: ' + data.content, 'error');
                break;
                
            case 'interview_ended':
                this.showInterviewSummary(data.summary);
                break;
                
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    
    addMessageToChat(type, content, timestamp = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message message-${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-timestamp';
        timeDiv.textContent = InterviewApp.formatTime(timestamp || new Date().toISOString());
        
        messageDiv.appendChild(contentDiv);
        messageDiv.appendChild(timeDiv);
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    showToolActivity(tool, status) {
        const indicator = document.createElement('span');
        indicator.className = 'tool-indicator';
        indicator.textContent = this.getToolIcon(tool) + ' ' + tool;
        
        document.getElementById('tool-indicators').appendChild(indicator);
        
        // Remove after delay if status is 'complete'
        if (status === 'complete') {
            setTimeout(() => {
                indicator.remove();
            }, 2000);
        }
    }
    
    getToolIcon(tool) {
        const icons = {
            'search': '🇸',
            'database': '🇩',
            'code': '💻',
            'research': '🔍',
            'analysis': '📊'
        };
        return icons[tool] || '🔧';
    }
    
    showTypingIndicator() {
        document.getElementById('typing-indicator').classList.remove('hidden');
    }
    
    hideTypingIndicator() {
        document.getElementById('typing-indicator').classList.add('hidden');
    }
    
    updateConnectionStatus(text, status) {
        document.getElementById('connection-status').textContent = text;
        document.getElementById('connection-status').className = `status-${status}`;
    }
    
    enableInput() {
        this.messageInput.disabled = false;
        this.sendButton.disabled = false;
        if (this.micButton && this.speechSupported) {
            this.micButton.disabled = false;
        }
        this.enableWhisperButton();
        this.messageInput.focus();
    }
    
    disableInput() {
        this.messageInput.disabled = true;
        this.sendButton.disabled = true;
        if (this.micButton) {
            this.micButton.disabled = true;
        }
        this.disableWhisperButton();
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    endInterview() {
        if (confirm('Are you sure you want to end the interview?')) {
            if (this.ws && this.isConnected) {
                this.ws.send(JSON.stringify({
                    type: 'end_interview',
                    timestamp: new Date().toISOString()
                }));
            }
            
            // Close WebSocket
            if (this.ws) {
                this.ws.close(1000, 'Interview ended by user');
            }
            
            // Generate summary (placeholder with honest messaging)
            setTimeout(() => {
                this.showInterviewSummary({
                    duration: '[Placeholder - Not yet tracked]',
                    questionsAsked: '[Placeholder - Not yet counted]',
                    overallScore: '[Placeholder - AI scoring not implemented]',
                    strengths: [
                        '🚧 Interview analysis coming soon!',
                        'This will use AI to evaluate your responses',
                        'Real-time performance scoring will be added'
                    ],
                    improvements: [
                        '🚧 This is just a UI mockup',
                        'Actual feedback will analyze your specific answers',
                        'AI will provide personalized suggestions'
                    ]
                });
            }, 1000);
        }
    }
    
    showInterviewSummary(summary) {
        const modal = document.getElementById('summary-modal');
        const content = document.getElementById('summary-content');
        
        content.innerHTML = `
            <div class="summary-stats">
                <h4>📊 Interview Statistics</h4>
                <p><strong>Duration:</strong> ${summary.duration || 'N/A'}</p>
                <p><strong>Questions Asked:</strong> ${summary.questionsAsked || 'N/A'}</p>
                <p><strong>Overall Score:</strong> ${summary.overallScore || 'N/A'}</p>
            </div>
            
            <div class="summary-strengths">
                <h4>✅ Strengths</h4>
                <ul>
                    ${(summary.strengths || []).map(s => `<li>${s}</li>`).join('')}
                </ul>
            </div>
            
            <div class="summary-improvements">
                <h4>📈 Areas for Improvement</h4>
                <ul>
                    ${(summary.improvements || []).map(i => `<li>${i}</li>`).join('')}
                </ul>
            </div>
        `;
        
        modal.classList.remove('hidden');
        
        // Setup modal event listeners
        document.getElementById('close-summary').onclick = () => {
            modal.classList.add('hidden');
        };
        
        document.getElementById('new-interview').onclick = () => {
            window.location.href = '/';
        };
    }
    
    // Speech Recognition Methods
    setupSpeechRecognition() {
        console.log('Setting up speech recognition...', {
            speechSupported: this.speechSupported,
            micButton: this.micButton
        });
        
        if (!this.speechSupported) {
            console.warn('Speech recognition not supported in this browser');
            if (this.micButton) {
                this.micButton.style.display = 'none';
            }
            return;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        // Configure recognition
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        // Event handlers
        this.recognition.onstart = () => {
            this.isListening = true;
            this.speechStatus.classList.remove('hidden');
            this.micButton.style.background = '#e74c3c';
            this.micButton.title = 'Stop listening';
            
            // Stop interviewer voice when user starts speaking
            this.stopSpeech();
            
            // Start audio recording for Whisper
            this.startAudioRecording();
        };
        
        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Add final results to accumulated transcript
            if (finalTranscript) {
                this.accumulatedTranscript += finalTranscript;
            }
            
            // Display accumulated + interim transcript
            const fullTranscript = this.accumulatedTranscript + interimTranscript;
            if (fullTranscript.trim()) {
                this.messageInput.value = fullTranscript;
                // Auto-resize textarea
                this.messageInput.style.height = 'auto';
                this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
            }
        };
        
        this.recognition.onend = () => {
            // Only stop if user intentionally stopped listening
            if (this.isListening) {
                console.log('Speech recognition ended, restarting...');
                try {
                    this.recognition.start(); // Restart automatically
                } catch (error) {
                    // Recognition might already be starting, ignore this error
                    console.log('Recognition restart error (likely already starting):', error);
                }
            } else {
                // User intentionally stopped, update UI and stop audio recording
                this.speechStatus.classList.add('hidden');
                this.micButton.style.background = '';
                this.micButton.title = 'Voice input';
                
                // Stop audio recording for Whisper
                this.stopAudioRecording();
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.isListening = false;
            this.speechStatus.classList.add('hidden');
            this.micButton.style.background = '';
            this.micButton.title = 'Voice input';
            
            // Show user-friendly error message
            if (event.error === 'not-allowed') {
                alert('Microphone access denied. Please allow microphone access to use voice input.');
            } else if (event.error === 'no-speech') {
                // Silent timeout is normal, don't show error
            } else {
                alert(`Speech recognition error: ${event.error}`);
            }
        };
    }
    
    toggleSpeechRecognition() {
        console.log('Microphone button clicked!', {
            speechSupported: this.speechSupported,
            recognition: this.recognition,
            isListening: this.isListening
        });
        
        if (!this.speechSupported || !this.recognition) {
            alert('Speech recognition is not supported in this browser. Please try Chrome, Edge, or Safari.');
            return;
        }
        
        if (this.isListening) {
            console.log('Stopping speech recognition...');
            this.isListening = false; // Set flag BEFORE stopping so onend handler knows user intended to stop
            
            // Force stop everything - even if disconnected
            try {
                this.recognition.stop();
            } catch (error) {
                console.log('Recognition stop error (expected if already stopped):', error);
            }
            
            // Force stop audio recording
            this.stopAudioRecording();
            
            // Force update UI
            this.speechStatus.classList.add('hidden');
            this.micButton.style.background = '';
            this.micButton.title = 'Voice input';
            
        } else {
            console.log('Starting speech recognition...');
            this.accumulatedTranscript = ''; // Reset accumulated transcript when starting fresh
            try {
                this.recognition.start();
            } catch (error) {
                console.error('Error starting speech recognition:', error);
                alert('Could not start voice input. Please make sure your microphone is available.');
            }
        }
    }
    
    // Audio Recording Methods for Whisper
    async setupAudioRecording() {
        console.log('Setting up audio recording for Whisper...');
        
        // Check if MediaRecorder is supported
        if (!window.MediaRecorder) {
            console.warn('MediaRecorder not supported, Whisper functionality disabled');
            this.hideWhisperButton('MediaRecorder not supported in this browser');
            return;
        }
        
        // Check if Whisper API is available
        try {
            const response = await fetch('/api/whisper-available');
            const data = await response.json();
            
            if (data.available) {
                console.log('Whisper transcription available');
                this.enableWhisperButton();
            } else {
                console.log('Whisper not available:', data.reason);
                this.hideWhisperButton('Whisper requires OpenAI API key');
            }
        } catch (error) {
            console.error('Error checking Whisper availability:', error);
            this.hideWhisperButton('Unable to connect to transcription service');
        }
    }
    
    startAudioRecording() {
        if (this.isRecording || !this.isConnected) return;
        
        console.log('Starting audio recording...');
        
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.audioChunks = [];
                this.mediaRecorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm;codecs=opus'
                });
                
                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        this.audioChunks.push(event.data);
                    }
                };
                
                this.mediaRecorder.start(100); // Collect data every 100ms
                this.isRecording = true;
                console.log('Audio recording started');
            })
            .catch(error => {
                console.error('Error starting audio recording:', error);
            });
    }
    
    stopAudioRecording() {
        if (!this.isRecording || !this.mediaRecorder) {
            // Even if not officially recording, try to clean up any streams
            this.forceStopAllStreams();
            return Promise.resolve(null);
        }
        
        console.log('Stopping audio recording...');
        
        return new Promise((resolve) => {
            const cleanup = () => {
                this.isRecording = false;
                
                // Stop all tracks to release microphone
                if (this.mediaRecorder && this.mediaRecorder.stream) {
                    this.mediaRecorder.stream.getTracks().forEach(track => {
                        try {
                            track.stop();
                        } catch (e) {
                            console.log('Error stopping track:', e);
                        }
                    });
                }
                
                const audioBlob = this.audioChunks.length > 0 ? 
                    new Blob(this.audioChunks, { type: 'audio/webm' }) : null;
                
                console.log('Audio recording stopped, blob size:', audioBlob?.size || 0);
                resolve(audioBlob);
            };
            
            try {
                this.mediaRecorder.onstop = cleanup;
                this.mediaRecorder.stop();
            } catch (error) {
                console.log('Error stopping media recorder:', error);
                cleanup(); // Still clean up
            }
        });
    }
    
    forceStopAllStreams() {
        // Emergency cleanup method
        if (this.mediaRecorder && this.mediaRecorder.stream) {
            this.mediaRecorder.stream.getTracks().forEach(track => {
                try {
                    track.stop();
                } catch (e) {
                    console.log('Error force-stopping track:', e);
                }
            });
        }
        this.isRecording = false;
    }
    
    async transcribeWithWhisper() {
        if (!this.audioChunks.length || this.audioChunks.length === 0) {
            alert('No audio recorded. Please use the microphone to record speech first.');
            return;
        }
        
        console.log('Transcribing with Whisper...');
        
        try {
            // Update button state
            this.whisperButton.classList.add('processing');
            this.whisperButton.disabled = true;
            this.whisperButton.title = 'Processing with Whisper...';
            
            // Create audio blob from recorded chunks
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
            
            // Create form data
            const formData = new FormData();
            formData.append('audio_file', audioBlob, 'recording.webm');
            formData.append('session_id', this.sessionId);
            
            // Send to Whisper API
            const response = await fetch('/api/whisper-transcribe', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Transcription failed');
            }
            
            const data = await response.json();
            
            if (data.success && data.transcript) {
                // Replace the current text with Whisper's more accurate transcription
                this.messageInput.value = data.transcript;
                this.accumulatedTranscript = data.transcript;
                
                // Auto-resize textarea
                this.messageInput.style.height = 'auto';
                this.messageInput.style.height = this.messageInput.scrollHeight + 'px';
                
                console.log('Whisper transcription successful:', data.transcript);
            } else {
                throw new Error('No transcript received');
            }
            
        } catch (error) {
            console.error('Whisper transcription error:', error);
            alert(`Whisper transcription failed: ${error.message}`);
        } finally {
            // Reset button state
            this.whisperButton.classList.remove('processing');
            this.whisperButton.disabled = false;
            this.whisperButton.title = 'Refine with Whisper (High Accuracy)';
        }
    }
    
    enableWhisperButton() {
        if (this.whisperButton && this.isConnected) {
            this.whisperButton.disabled = false;
            this.whisperButton.style.display = '';
            this.whisperButton.title = 'Refine with Whisper (High Accuracy)';
        }
    }
    
    disableWhisperButton() {
        if (this.whisperButton) {
            this.whisperButton.disabled = true;
        }
    }
    
    hideWhisperButton(reason) {
        if (this.whisperButton) {
            this.whisperButton.style.display = 'none';
            this.whisperButton.title = reason || 'Whisper not available';
            console.log('Whisper button hidden:', reason);
        }
        
        // Show helpful message if it's about missing OpenAI key
        const whisperInfo = document.getElementById('whisper-info');
        if (whisperInfo && reason && reason.includes('OpenAI')) {
            whisperInfo.classList.remove('hidden');
        }
    }
    
    // Voice Synthesis Methods
    async setupVoiceSynthesis() {
        console.log('Setting up voice synthesis...');
        
        // Check if Speech Synthesis is supported
        if (!this.speechSynth) {
            console.warn('Speech Synthesis not supported in this browser');
            this.hideVoiceControls('Speech synthesis not supported');
            return;
        }
        
        // Load available voices
        this.loadVoices();
        
        // Setup voice control event listeners
        this.setupVoiceEventListeners();
        
        // Check if OpenAI TTS is available
        try {
            const response = await fetch('/api/whisper-available'); // Reuse this endpoint
            const data = await response.json();
            this.openaiTtsAvailable = data.available;
            
            if (this.openaiTtsAvailable) {
                console.log('Premium TTS (OpenAI) available');
            } else {
                console.log('Using browser TTS only');
            }
        } catch (error) {
            console.error('Error checking TTS availability:', error);
        }
    }
    
    loadVoices() {
        this.availableVoices = this.speechSynth.getVoices();
        
        // If voices are not immediately available, wait for them
        if (this.availableVoices.length === 0) {
            this.speechSynth.addEventListener('voiceschanged', () => {
                this.availableVoices = this.speechSynth.getVoices();
                console.log(`Loaded ${this.availableVoices.length} voices`);
            });
        }
    }
    
    setupVoiceEventListeners() {
        // Voice toggle
        if (this.voiceToggle) {
            this.voiceToggle.addEventListener('change', (e) => {
                this.voiceEnabled = e.target.checked;
                console.log('Voice enabled:', this.voiceEnabled);
                
                // Stop current speech if voice is disabled
                if (!this.voiceEnabled) {
                    this.stopSpeech();
                }
            });
        }
        
        // Voice speed slider
        if (this.voiceSpeedSlider) {
            this.voiceSpeedSlider.addEventListener('input', (e) => {
                this.voiceSpeed = parseFloat(e.target.value);
                if (this.speedValueDisplay) {
                    this.speedValueDisplay.textContent = `${this.voiceSpeed.toFixed(1)}x`;
                }
            });
        }
        
        // TTS (OpenAI) toggle
        if (this.ttsToggle) {
            this.ttsToggle.addEventListener('change', async (e) => {
                this.ttsEnabled = e.target.checked;
                console.log('TTS enabled:', this.ttsEnabled);
                
                // Update session setting
                try {
                    await this.updateSessionTtsSetting(this.ttsEnabled);
                } catch (error) {
                    console.error('Failed to update TTS setting:', error);
                    // Revert toggle on failure
                    e.target.checked = !this.ttsEnabled;
                    this.ttsEnabled = !this.ttsEnabled;
                }
                
                // Stop current speech if TTS is disabled
                if (!this.ttsEnabled) {
                    this.stopSpeech();
                }
            });
        }
    }
    
    async speakText(text) {
        if (!this.voiceEnabled || !text.trim()) {
            return;
        }
        
        // Stop any current speech
        this.stopSpeech();
        
        // Clean the text (remove markdown, etc.)
        const cleanText = this.cleanTextForSpeech(text);
        
        // Try OpenAI TTS first if available and enabled
        if (this.openaiTtsAvailable && this.ttsEnabled) {
            try {
                const result = await this.speakWithOpenAI(cleanText);
                if (result && !result.disabled) {
                    return; // Successfully used OpenAI TTS
                }
            } catch (error) {
                console.warn('OpenAI TTS failed, falling back to browser TTS:', error);
            }
        }
        
        // Fallback to browser speech synthesis
        this.speakWithBrowser(cleanText);
    }
    
    async speakWithOpenAI(text) {
        try {
            const response = await fetch('/api/tts-synthesize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    text: text,
                    session_id: this.sessionId 
                })
            });
            
            if (!response.ok) {
                throw new Error(`TTS request failed: ${response.status}`);
            }
            
            // Check if response is JSON (TTS disabled) or audio blob
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const result = await response.json();
                if (result.disabled) {
                    console.log('TTS disabled, skipping OpenAI synthesis');
                    return { disabled: true };
                }
            }
            
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            
            // Store reference to current speech
            this.currentSpeech = audio;
            
            // Set playback rate
            audio.playbackRate = this.voiceSpeed;
            
            // Play the audio
            await audio.play();
            
            // Clean up when done
            audio.addEventListener('ended', () => {
                URL.revokeObjectURL(audioUrl);
                if (this.currentSpeech === audio) {
                    this.currentSpeech = null;
                }
            });
            
            return { disabled: false };
            
        } catch (error) {
            console.error('OpenAI TTS error:', error);
            throw error;
        }
    }
    
    speakWithBrowser(text) {
        if (!this.speechSynth) return;
        
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Configure voice settings
        utterance.rate = this.voiceSpeed;
        utterance.pitch = 1;
        utterance.volume = 1;
        
        // Try to use a good voice
        if (this.availableVoices.length > 0) {
            // Prefer English voices
            const englishVoice = this.availableVoices.find(voice => 
                voice.lang.startsWith('en-') && !voice.name.includes('Google')
            ) || this.availableVoices.find(voice => voice.lang.startsWith('en-'));
            
            if (englishVoice) {
                utterance.voice = englishVoice;
            }
        }
        
        // Store reference to current speech
        this.currentSpeech = utterance;
        
        // Clean up when done
        utterance.addEventListener('end', () => {
            if (this.currentSpeech === utterance) {
                this.currentSpeech = null;
            }
        });
        
        utterance.addEventListener('error', (e) => {
            console.error('Speech synthesis error:', e);
            if (this.currentSpeech === utterance) {
                this.currentSpeech = null;
            }
        });
        
        this.speechSynth.speak(utterance);
    }
    
    stopSpeech() {
        if (this.currentSpeech) {
            if (this.currentSpeech instanceof Audio) {
                // OpenAI TTS audio
                this.currentSpeech.pause();
                this.currentSpeech.currentTime = 0;
            } else {
                // Browser speech synthesis
                this.speechSynth.cancel();
            }
            this.currentSpeech = null;
        }
    }
    
    cleanTextForSpeech(text) {
        // Remove markdown formatting
        return text
            .replace(/\*\*(.*?)\*\*/g, '$1')  // Bold
            .replace(/\*(.*?)\*/g, '$1')      // Italic
            .replace(/`(.*?)`/g, '$1')        // Code
            .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Links
            .replace(/#{1,6}\s*/g, '')        // Headers
            .replace(/\n+/g, ' ')             // Multiple newlines
            .replace(/\s+/g, ' ')             // Multiple spaces
            .trim();
    }
    
    hideVoiceControls(reason) {
        const voiceControls = document.querySelector('.voice-controls');
        if (voiceControls) {
            voiceControls.style.display = 'none';
            console.log('Voice controls hidden:', reason);
        }
    }
    
    // Cost Tracking Methods
    updateCostDisplay(costData) {
        // More robust check for undefined/null costData
        if (costData === undefined || costData === null) {
            console.warn('updateCostDisplay called with undefined/null costData');
            return;
        }
        
        // Additional check to ensure costData is an object
        if (typeof costData !== 'object') {
            console.warn('updateCostDisplay called with non-object costData:', costData);
            return;
        }
        
        console.log('updateCostDisplay called with:', costData);
        console.log('costData type:', typeof costData);
        console.log('costData is null:', costData === null);
        console.log('costData is undefined:', costData === undefined);
        
        // Handle case where costData is undefined or null
        if (!costData) {
            console.warn('updateCostDisplay called with undefined costData');
            return;
        }
        
        console.log('costData.total_cost_usd:', costData.total_cost_usd);
        
        let costWidget = document.getElementById('cost-widget');
        
        // Create cost widget if it doesn't exist
        if (!costWidget) {
            costWidget = this.createCostWidget();
        }
        
        // Update the display with safe defaults
        const totalCost = costData.total_cost_usd || 0;
        const tokenStats = costData.token_stats || {};
        const breakdown = costData.cost_breakdown || {};
        
        const costContent = document.getElementById('cost-content');
        if (costContent) {
            costContent.innerHTML = `
                <div class="cost-summary">
                    <strong>Total: $${totalCost.toFixed(4)}</strong>
                    <span class="cost-duration">${costData.duration_minutes || 0}min</span>
                </div>
                <div class="cost-details">
                    <div class="token-stats">
                        <span>📝 ${tokenStats.total_tokens || 0} tokens</span>
                        ${tokenStats.audio_minutes ? `<span>🎤 ${tokenStats.audio_minutes}min audio</span>` : ''}
                        ${tokenStats.tts_characters ? `<span>🔊 ${tokenStats.tts_characters} chars TTS</span>` : ''}
                    </div>
                    <div class="service-breakdown">
                        ${this.formatCostBreakdown(breakdown)}
                    </div>
                </div>
            `;
        }
    }
    
    createCostWidget() {
        const widget = document.createElement('div');
        widget.id = 'cost-widget';
        widget.className = 'cost-widget';
        widget.innerHTML = `
            <div class="cost-header">
                <span class="cost-icon">💰</span>
                <span>API Costs</span>
                <button class="cost-toggle" onclick="this.parentElement.parentElement.classList.toggle('minimized')">−</button>
            </div>
            <div id="cost-content" class="cost-content">
                <div class="cost-summary">
                    <strong>Total: $0.0000</strong>
                    <span class="cost-duration">0min</span>
                </div>
            </div>
        `;
        
        document.body.appendChild(widget);
        return widget;
    }
    
    formatCostBreakdown(breakdown) {
        let html = '';
        
        for (const [provider, services] of Object.entries(breakdown)) {
            for (const [service, cost] of Object.entries(services)) {
                if (cost > 0) {
                    const providerIcon = provider === 'openai' ? '🤖' : '🧠';
                    html += `<span class="service-cost">${providerIcon} ${service}: $${cost.toFixed(4)}</span>`;
                }
            }
        }
        
        return html || '<span class="no-costs">No costs yet</span>';
    }
    
    // Update TTS setting on server
    async updateSessionTtsSetting(enabled) {
        try {
            const response = await fetch('/api/update-tts-setting', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    tts_enabled: enabled
                })
            });
            
            if (!response.ok) {
                throw new Error(`Failed to update TTS setting: ${response.status}`);
            }
            
            console.log('TTS setting updated successfully:', enabled);
        } catch (error) {
            console.error('Error updating TTS setting:', error);
            throw error;
        }
    }

    // Code Editor Methods
    setupCodeEditor() {
        const runCodeBtn = document.getElementById('run-code');
        const clearCodeBtn = document.getElementById('clear-code');
        const clearOutputBtn = document.getElementById('clear-output');
        const codeEditor = document.getElementById('code-editor');
        const codeOutput = document.getElementById('code-output');

        if (!runCodeBtn || !clearCodeBtn || !clearOutputBtn || !codeEditor || !codeOutput) {
            return; // Code editor not present (non-technical interview)
        }

        // Run code button
        runCodeBtn.addEventListener('click', () => {
            this.runCode();
        });

        // Clear code button
        clearCodeBtn.addEventListener('click', () => {
            codeEditor.value = '';
            codeEditor.focus();
        });

        // Clear output button
        clearOutputBtn.addEventListener('click', () => {
            this.clearOutput();
        });

        // Tab key support for code editor
        codeEditor.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                e.preventDefault();
                const start = codeEditor.selectionStart;
                const end = codeEditor.selectionEnd;
                codeEditor.value = codeEditor.value.substring(0, start) + '    ' + codeEditor.value.substring(end);
                codeEditor.selectionStart = codeEditor.selectionEnd = start + 4;
            }
        });

        console.log('Code editor initialized');
    }

    async runCode() {
        const codeEditor = document.getElementById('code-editor');
        const codeOutput = document.getElementById('code-output');
        const langSelect = document.getElementById('code-language');
        const language = (langSelect && langSelect.value) ? langSelect.value : 'python';
        
        if (!codeEditor || !codeOutput) return;

        const code = codeEditor.value.trim();
        if (!code) {
            this.showOutput('Please enter some code to run.');
            return;
        }

        // Show spinner entry
        this.showOutput('⏳ Running...');

        try {
            const response = await fetch('/api/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language, code, session_id: this.sessionId })
            });
            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || `Execution failed (${response.status})`);
            }
            const result = await response.json();

            let output = '';
            if (result.stdout) output += result.stdout + '\n';
            if (result.stderr) output += (output ? '\n' : '') + '[stderr]\n' + result.stderr + '\n';
            if (!output.trim()) output = '(no output)';
            output += `\n\n[${language} • ${result.duration_ms} ms]`;

            if (language === 'sql' && result.table) {
                const cols = result.table.columns || [];
                const rows = result.table.rows || [];
                const header = cols.join(' | ');
                const sep = cols.map(() => '---').join(' | ');
                const body = rows.map(r => r.join(' | ')).join('\n');
                output += `\n\n${header}\n${sep}\n${body}`;
            }

            this.showOutput(output);
        } catch (err) {
            this.showOutput(`❌ ${err.message || err}`);
        }
    }

    showOutput(message) {
        const codeOutput = document.getElementById('code-output');
        if (!codeOutput) return;

        const timestamp = new Date().toLocaleTimeString();
        const outputDiv = document.createElement('div');
        outputDiv.className = 'output-entry';
        outputDiv.innerHTML = `
            <div class="output-timestamp">[${timestamp}]</div>
            <pre class="output-content">${message}</pre>
        `;

        // Clear placeholder if it exists
        const placeholder = codeOutput.querySelector('.output-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        codeOutput.appendChild(outputDiv);
        codeOutput.scrollTop = codeOutput.scrollHeight;
    }

    clearOutput() {
        const codeOutput = document.getElementById('code-output');
        if (!codeOutput) return;

        codeOutput.innerHTML = `
            <div class="output-placeholder">
                <p>💡 <strong>Code Editor Ready</strong></p>
                <p>Write your code in the editor above and click "Run Code" to execute it.</p>
                <p>Supported languages: Python, SQL</p>
            </div>
        `;
    }
}

// Initialize interview chat when page loads
document.addEventListener('DOMContentLoaded', function() {
    const sessionId = document.querySelector('meta[name="session-id"]')?.content;
    if (sessionId) {
        window.interviewChat = new InterviewChat(sessionId);
        console.log('Interview chat initialized for session:', sessionId);
        
        // Initialize TTS settings from session
        const ttsEnabled = document.querySelector('meta[name="tts-enabled"]')?.content === 'True';
        const ttsVoice = document.querySelector('meta[name="tts-voice"]')?.content || 'alloy';
        
        // Set initial TTS toggle state
        if (window.interviewChat.ttsToggle) {
            window.interviewChat.ttsToggle.checked = ttsEnabled;
            window.interviewChat.ttsEnabled = ttsEnabled;
        }
        
        console.log('TTS settings initialized:', { ttsEnabled, ttsVoice });
    }
});