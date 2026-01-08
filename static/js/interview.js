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
        this.setupResizeHandles();
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
            
            // Immediately sync TTS settings to ensure initial message uses correct TTS
            this.syncTtsSettingsOnConnect();
            
            // Send any queued messages
            while (this.messageQueue.length > 0) {
                const message = this.messageQueue.shift();
                this.ws.send(JSON.stringify(message));
            }
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'coding_prompt') {
                try {
                    this.insertProblemIntoEditor(data.content, data.question_number);
                } catch (e) {
                    console.error('Failed to insert coding prompt:', e);
                }
                return; // don't let TTS read this
            }
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
            case 'coding_prompt':
                this.insertProblemIntoEditor(data.content, data.question_number);
                // Also show a tiny confirmation line in chat
                this.addMessageToChat('interviewer', 'Coding prompt added to the editor.', data.timestamp);
                this.enableInput();
                break;
                
            case 'clear_editor':
                this.clearCodeEditor();
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
    
    async endInterview() {
        if (confirm('Are you sure you want to end the interview?')) {
            if (this.ws && this.isConnected) {
                this.ws.send(JSON.stringify({
                    type: 'end_interview',
                    timestamp: new Date().toISOString()
                }));
            }
            
            // Show loading state
            const modal = document.getElementById('summary-modal');
            if (modal) {
                modal.classList.remove('hidden');
                const content = document.getElementById('summary-content');
                if (content) {
                    content.innerHTML = '<div style="text-align: center; padding: 20px;"><p>🤖 Generating comprehensive interview report...</p><p>This analyzes your entire conversation history.</p></div>';
                }
            }
            
            try {
                const response = await fetch(`/api/evaluate-session/${this.sessionId}`, {
                    method: 'POST'
                });
                
                if (!response.ok) {
                    throw new Error('Evaluation failed');
                }
                
                const report = await response.json();
                this.showInterviewSummary(report);
                
            } catch (error) {
                const content = document.getElementById('summary-content');
                if (content) {
                    content.innerHTML = `<div class="error" style="color: red; padding: 20px;">Failed to generate report: ${error.message}</div>`;
                }
                console.error('Evaluation error:', error);
            }
            
            // Close WebSocket
            if (this.ws) {
                this.ws.close(1000, 'Interview ended by user');
            }
        }
    }
    
    showInterviewSummary(summary) {
        const modal = document.getElementById('summary-modal');
        const content = document.getElementById('summary-content');
        
        content.innerHTML = `
            <div class="summary-container" style="padding: 20px;">
                <div class="summary-header" style="text-align: center; margin-bottom: 20px;">
                    <div class="score-display" style="font-size: 3rem; font-weight: bold; color: ${summary.score >= 7 ? '#2ea043' : '#d29922'};">
                        ${summary.score}/10
                    </div>
                    <h4>Overall Score</h4>
                </div>
                
                <div class="summary-section" style="margin-bottom: 20px;">
                    <h5>Executive Summary</h5>
                    <p>${summary.summary}</p>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <div class="summary-strengths">
                        <h5 style="color: #2ea043;">✅ Strengths</h5>
                        <ul>
                            ${(summary.strengths || []).map(s => `<li>${s}</li>`).join('')}
                        </ul>
                    </div>
                    
                    <div class="summary-improvements">
                        <h5 style="color: #d29922;">📈 Areas for Improvement</h5>
                        <ul>
                            ${(summary.improvements || []).map(i => `<li>${i}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                
                <div class="summary-assessments" style="background: #161b22; padding: 15px; border-radius: 6px; color: #e6edf3;">
                    <div style="margin-bottom: 10px;">
                        <strong style="color: #58a6ff;">Communication:</strong> ${summary.communication_assessment}
                    </div>
                    <div style="margin-bottom: 10px;">
                        <strong style="color: #58a6ff;">Cultural Fit:</strong> ${summary.cultural_fit_assessment}
                    </div>
                    ${summary.technical_assessment ? `
                    <div>
                        <strong style="color: #58a6ff;">Technical:</strong> ${summary.technical_assessment}
                    </div>` : ''}
                </div>
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
    
    // Sync TTS settings immediately when WebSocket connects
    async syncTtsSettingsOnConnect() {
        try {
            // Get TTS settings from meta tags (set by server)
            const ttsEnabled = document.querySelector('meta[name="tts-enabled"]')?.content === 'True';
            const ttsVoice = document.querySelector('meta[name="tts-voice"]')?.content || 'alloy';
            
            console.log('Syncing TTS settings on connect:', { ttsEnabled, ttsVoice });
            
            // Update local state
            this.ttsEnabled = ttsEnabled;
            if (this.ttsToggle) {
                this.ttsToggle.checked = ttsEnabled;
            }
            
            // Send TTS settings to server and wait for it to complete
            try {
                await this.updateSessionTtsSetting(ttsEnabled);
                console.log('TTS settings synchronized successfully');
            } catch (error) {
                console.error('Failed to sync TTS settings on connect:', error);
            }
            
            // After TTS is synced, tell server client is ready for initial message
            this.sendClientReady();
        } catch (error) {
            console.error('Error syncing TTS settings on connect:', error);
            // Still send client ready even if TTS sync fails
            this.sendClientReady();
        }
    }

    // Send client ready signal to receive initial message with correct TTS
    sendClientReady() {
        if (this.ws && this.isConnected) {
            console.log('Sending client ready signal');
            this.ws.send(JSON.stringify({
                type: 'client_ready',
                timestamp: new Date().toISOString()
            }));
        }
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
        const clearOutputBtn = document.getElementById('clear-output');
        const codeEditor = document.getElementById('code-editor');
        const codeOutput = document.getElementById('code-output');
        const askHintBtn = document.getElementById('ask-hint');
        const explainErrorBtn = document.getElementById('explain-error');
        const whatNextBtn = document.getElementById('what-next');
        const viewSetupBtn = document.getElementById('view-setup');
        const submitEvalBtn = document.getElementById('submit-eval');

        if (!runCodeBtn || !clearOutputBtn || !codeEditor || !codeOutput) {
            return; // Code editor not present (non-technical interview)
        }

        // Run code button
        runCodeBtn.addEventListener('click', () => {
            this.runCode();
        });

        // Clear output button
        clearOutputBtn.addEventListener('click', () => {
            this.clearOutput();
        });

        // Hint buttons
        if (askHintBtn) {
            askHintBtn.addEventListener('click', () => this.sendHintRequest('problem'));
        }
        if (explainErrorBtn) {
            explainErrorBtn.addEventListener('click', () => this.sendHintRequest('error'));
        }
        if (whatNextBtn) {
            whatNextBtn.addEventListener('click', () => this.sendHintRequest('next'));
        }

        if (submitEvalBtn) {
            submitEvalBtn.addEventListener('click', () => this.evaluateSolution());
        }

        if (viewSetupBtn) {
            viewSetupBtn.addEventListener('click', async () => {
                try {
                    const resp = await fetch(`/api/data-setup?session_id=${this.sessionId}`);
                    const data = await resp.json();
                    const blocks = [];
                    if (data.python_setup) blocks.push(`Python setup:\n\n${data.python_setup}`);
                    if (data.sql_setup) blocks.push(`SQL setup:\n\n${data.sql_setup}`);
                    this.showOutput(blocks.join('\n\n') || 'No setup blocks detected. The problem may not include explicit setup.');
                } catch (e) {
                    this.showOutput('Could not retrieve data setup.');
                }
            });
        }

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

        // Set up syntax highlighting
        this.setupSyntaxHighlighting(codeEditor);

        console.log('Code editor initialized');
    }

    getLanguageFromTrack() {
        const metaTrack = document.querySelector('meta[name="technical-track"]');
        const track = metaTrack ? metaTrack.content : '';
        if (track === 'sql') return 'sql';
        return 'python';
    }

    setupSyntaxHighlighting(editor) {
        // Force disable spellcheck via HTML attributes (more reliable than CSS)
        editor.setAttribute('spellcheck', 'false');
        editor.setAttribute('autocomplete', 'off');
        editor.setAttribute('autocorrect', 'off');
        editor.setAttribute('autocapitalize', 'off');
        
        // Remove any existing overlays that might cause issues
        const existingOverlay = editor.parentNode.querySelector('.pandas-highlight-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }
        
        // Set up smart highlighting with better performance
        this.setupSmartHighlighting(editor);
        this.setupSyntaxHighlighting2(editor);
        
        console.log('Code editor styled with enhanced syntax highlighting and spellcheck disabled');
    }

    setupSyntaxHighlighting2(editor) {
        // Add language-specific CSS class based on current track
        const track = this.getLanguageFromTrack();
        editor.classList.add(`code-${track}`);
        
        // Create a simple syntax highlighter
        const highlightCode = () => {
            const code = editor.value;
            if (!code.trim()) return;
            
            // Simple keyword highlighting via text selection hints
            this.addSyntaxHints(editor, code, track);
        };
        
        // Add event listeners for real-time highlighting
        editor.addEventListener('input', highlightCode);
        editor.addEventListener('keyup', highlightCode);
        
        // Initial highlighting
        highlightCode();
    }

    addSyntaxHints(editor, code, language) {
        // Add subtle visual cues for syntax elements
        const lines = code.split('\n');
        let hasKeywords = false;
        
        if (language === 'python') {
            const pythonKeywords = ['def', 'import', 'from', 'if', 'else', 'for', 'while', 'return', 'class', 'try', 'except', 'with', 'as'];
            hasKeywords = pythonKeywords.some(keyword => code.includes(keyword));
        } else if (language === 'sql') {
            const sqlKeywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY', 'INSERT', 'UPDATE', 'DELETE'];
            hasKeywords = sqlKeywords.some(keyword => code.toUpperCase().includes(keyword));
        }
        
        // Subtle border color change to indicate syntax recognition
        if (hasKeywords) {
            editor.style.borderColor = '#58a6ff';
            setTimeout(() => {
                editor.style.borderColor = '#30363d';
            }, 1000);
        }
    }

    setupSmartHighlighting(editor) {
        // Create a lightweight highlighting system using textarea selection
        const container = editor.parentNode;
        
        // Add event listeners for real-time highlighting hints
        editor.addEventListener('input', () => this.updateSmartHighlighting(editor));
        editor.addEventListener('keyup', () => this.updateSmartHighlighting(editor));
        editor.addEventListener('focus', () => this.showSyntaxHints(editor));
        
        // Initial highlighting
        this.updateSmartHighlighting(editor);
    }

    updateSmartHighlighting(editor) {
        const code = editor.value;
        if (!code.trim()) return;
        
        // Smart bracket matching and indentation assistance
        this.assistBracketMatching(editor);
        this.assistPandasCompletion(editor);
    }

    assistBracketMatching(editor) {
        const cursorPos = editor.selectionStart;
        const code = editor.value;
        const char = code[cursorPos - 1];
        
        // Flash matching brackets briefly
        if (['(', ')', '[', ']', '{', '}'].includes(char)) {
            editor.style.transition = 'box-shadow 0.2s ease';
            editor.style.boxShadow = '0 0 8px rgba(100, 149, 237, 0.5)';
            setTimeout(() => {
                editor.style.boxShadow = 'none';
            }, 200);
        }
    }

    assistPandasCompletion(editor) {
        const cursorPos = editor.selectionStart;
        const code = editor.value;
        const lineStart = code.lastIndexOf('\n', cursorPos - 1) + 1;
        const currentLine = code.substring(lineStart, cursorPos);
        
        // Show subtle visual feedback for pandas operations
        if (currentLine.includes('df.') || currentLine.includes('pd.')) {
            editor.style.borderColor = '#a5d6ff';
            setTimeout(() => {
                editor.style.borderColor = '#30363d';
            }, 1000);
        }
    }

    showSyntaxHints(editor) {
        // Create a tooltip with pandas shortcuts
        this.createSyntaxTooltip(editor);
    }

    createSyntaxTooltip(editor) {
        // Remove existing tooltip
        const existingTooltip = document.querySelector('.pandas-tooltip');
        if (existingTooltip) {
            existingTooltip.remove();
        }
        
        const tooltip = document.createElement('div');
        tooltip.className = 'pandas-tooltip';
        tooltip.style.cssText = `
            position: absolute;
            top: -40px;
            right: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: #e6edf3;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-family: 'Fira Code', monospace;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            white-space: nowrap;
            border: 1px solid #30363d;
        `;
        
        tooltip.innerHTML = `
            <span style="color: #a5d6ff;">df</span><span style="color: #d2a8ff;">.head()</span> | 
            <span style="color: #a5d6ff;">df</span><span style="color: #d2a8ff;">.groupby()</span> | 
            <span style="color: #ffa657;">pd.DataFrame()</span>
        `;
        
        editor.parentNode.style.position = 'relative';
        editor.parentNode.appendChild(tooltip);
        
        // Fade in
        setTimeout(() => {
            tooltip.style.opacity = '1';
        }, 100);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            if (tooltip.parentNode) {
                tooltip.style.opacity = '0';
                setTimeout(() => {
                    if (tooltip.parentNode) {
                        tooltip.remove();
                    }
                }, 300);
            }
        }, 3000);
    }

    updatePandasHighlighting() {
        // Smart highlighting is now handled by the new system
        const editor = document.getElementById('code-editor');
        if (editor) {
            this.updateSmartHighlighting(editor);
        }
    }

    updateSyntaxHighlighting() {
        // Delegate to the enhanced highlighting system
        this.updatePandasHighlighting();
    }

    evaluateSolution() {
        if (!this.ws || !this.isConnected) return;
        const codeEditor = document.getElementById('code-editor');
        const language = this.getLanguageFromTrack();
        const code = (codeEditor && codeEditor.value) ? codeEditor.value : '';
        
        if (!code.trim()) {
            this.showOutput('Please write some code before submitting for evaluation.');
            return;
        }
        
        // Show loading state
        this.showOutput('🔄 Evaluating your solution...\n\nThe interviewer is reviewing your code and will provide detailed feedback.');
        
        this.ws.send(JSON.stringify({
            type: 'evaluate_solution',
            language,
            code,
            timestamp: new Date().toISOString()
        }));
        this.showTypingIndicator();
    }

    async runCode() {
        const codeEditor = document.getElementById('code-editor');
        const codeOutput = document.getElementById('code-output');
        const language = this.getLanguageFromTrack();
        
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

            // Notify interviewer over WebSocket
            if (this.ws && this.isConnected) {
                try {
             this.ws.send(JSON.stringify({
                        type: 'code_run',
                        language,
                        code,
                        result
                    }));
                } catch (e) {
                    console.warn('Failed to notify code_run:', e);
                }
            }
        } catch (err) {
            this.showOutput(`❌ ${err.message || err}`);
        }
    }

    sendHintRequest(focus) {
        if (!this.ws || !this.isConnected) return;
        const codeEditor = document.getElementById('code-editor');
        const language = this.getLanguageFromTrack();
        const code = (codeEditor && codeEditor.value) ? codeEditor.value : '';
        try {
            this.ws.send(JSON.stringify({
                type: 'hint_request',
                focus,
                language,
                code
            }));
            // Show typing indicator to hint the user
            this.showTypingIndicator();
        } catch (e) {
            console.warn('Failed to send hint request:', e);
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

    clearCodeEditor() {
        const codeEditor = document.getElementById('code-editor');
        if (codeEditor) {
            codeEditor.value = '';
            console.log('DEBUG: Code editor cleared');
        }
    }

    insertProblemIntoEditor(problemText, questionNumber = 1) {
        console.log('DEBUG: insertProblemIntoEditor called with questionNumber:', questionNumber);
        const codeEditor = document.getElementById('code-editor');
        if (!codeEditor) return;
        const language = this.getLanguageFromTrack();
        const commentPrefix = language === 'sql' ? '-- ' : '# ';
        
        // Extract just the challenge question (remove data setup sections)
        const cleanProblem = this.extractChallengeOnly(problemText);
        
        const commented = cleanProblem
            .split('\n')
            .map(line => commentPrefix + line)
            .join('\n');
        
        // Add simple data preview code
        let previewCode = '';
        if (language === 'python') {
            previewCode = 'print(df.head())';
        } else if (language === 'sql') {
            previewCode = 'SELECT * FROM tbl LIMIT 5;';
        }
        
        const bundle = commented + '\n\n' + previewCode + '\n';
        
        // Always populate the editor with the new challenge
        // (Clearing is now handled separately by clear_editor message)
        console.log('DEBUG: Populating editor with new challenge');
        codeEditor.value = bundle;
        codeEditor.focus();
        
        // Update pandas syntax highlighting
        setTimeout(() => this.updatePandasHighlighting(), 0);
    }

    extractChallengeOnly(text) {
        // Look for ### Challenge Description section and extract just that
        const lines = text.split('\n');
        let challengeLines = [];
        let inChallenge = false;
        let inCodeBlock = false;
        
        for (let line of lines) {
            // Detect fenced code blocks
            if (line.trim().startsWith('```')) {
                inCodeBlock = !inCodeBlock;
                // Stop collecting challenge lines when we hit a code block
                if (inCodeBlock && inChallenge) {
                    break;
                }
                continue;
            }
            
            // Skip content inside code blocks
            if (inCodeBlock) continue;
            
            // Start collecting when we see Challenge Description
            if (line.includes('### Challenge Description') || line.includes('Challenge Description')) {
                inChallenge = true;
                continue; // Skip the header line itself
            }
            
            // Collect challenge description lines
            if (inChallenge && line.trim().length > 0) {
                challengeLines.push(line);
            }
        }
        
        let result = challengeLines.join('\n').trim();
        
        // If we didn't find a challenge section, try to extract the first meaningful content
        if (!result || result.length < 10) {
            // Look for the first non-header, non-code content
            for (let line of lines) {
                if (line.trim().startsWith('```') || line.trim().startsWith('#')) continue;
                if (line.trim().length > 20) {
                    result = line.trim();
                    break;
                }
            }
        }
        
        // Final fallback
        if (!result || result.length < 10) {
            result = "Complete the data analysis task using the provided dataset.";
        }
        
        return result;
    }



    extractPythonSignature(text) {
        if (!text) return null;
        // Try code block first
        const blockMatch = text.match(/```python([\s\S]*?)```/i);
        if (blockMatch && blockMatch[1]) {
            const lines = blockMatch[1].split('\n');
            const defLine = lines.find(l => /\bdef\s+[A-Za-z_]\w*\s*\(/.test(l));
            if (defLine) return defLine.trim();
        }
        // Try a single-line signature anywhere
        const defMatch = text.match(/def\s+[A-Za-z_]\w*\s*\([^\)]*\)\s*(->\s*[^:\n]+)?\s*:/);
        if (defMatch) return defMatch[0].trim();
        // Try to find a line following 'Function Signature:'
        const sigIdx = text.toLowerCase().indexOf('function signature');
        if (sigIdx !== -1) {
            const after = text.slice(sigIdx).split('\n')[0];
            const inLineDef = after.match(/def\s+[A-Za-z_]\w*\s*\([^\)]*\)\s*(->\s*[^:\n]+)?\s*:?/);
            if (inLineDef) return inLineDef[0].trim();
        }
        return null;
    }

    setupResizeHandles() {
        // Set up horizontal resize handle (between chat and coding sections)
        const chatCodingResizer = document.getElementById('chat-coding-resizer');
        if (chatCodingResizer) {
            this.setupHorizontalResize(chatCodingResizer);
        }

        // Set up vertical resize handle (between editor and output)
        const editorOutputResizer = document.getElementById('editor-output-resizer');
        if (editorOutputResizer) {
            this.setupVerticalResize(editorOutputResizer);
        }
    }

    setupHorizontalResize(resizer) {
        let isResizing = false;
        let startX = 0;
        let startLeftWidth = 0;
        let startRightWidth = 0;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            
            const container = resizer.parentElement;
            const chatSection = container.querySelector('.chat-section');
            const codingSection = container.querySelector('.coding-section');
            
            if (chatSection && codingSection) {
                startLeftWidth = chatSection.offsetWidth;
                startRightWidth = codingSection.offsetWidth;
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            
            // Prevent text selection during resize
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'col-resize';
        });

        function onMouseMove(e) {
            if (!isResizing) return;
            
            const container = resizer.parentElement;
            const totalWidth = container.offsetWidth - 6; // Subtract resizer width
            const deltaX = e.clientX - startX;
            
            // Calculate new widths
            let leftWidth = startLeftWidth + deltaX;
            let rightWidth = startRightWidth - deltaX;
            
            // Enforce minimum widths
            const minWidth = 300;
            if (leftWidth < minWidth) {
                leftWidth = minWidth;
                rightWidth = totalWidth - leftWidth;
            } else if (rightWidth < minWidth) {
                rightWidth = minWidth;
                leftWidth = totalWidth - rightWidth;
            }
            
            // Calculate percentages
            const leftPercent = (leftWidth / totalWidth) * 100;
            const rightPercent = (rightWidth / totalWidth) * 100;
            
            // Update grid template columns
            container.style.gridTemplateColumns = `${leftPercent}% 6px ${rightPercent}%`;
        }

        function onMouseUp() {
            isResizing = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
        }
    }

    setupVerticalResize(resizer) {
        let isResizing = false;
        let startY = 0;
        let startTopHeight = 0;
        let startBottomHeight = 0;

        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startY = e.clientY;
            
            const container = resizer.parentElement;
            const editorContainer = container.querySelector('.editor-container');
            const outputContainer = container.querySelector('.output-container');
            
            if (editorContainer && outputContainer) {
                startTopHeight = editorContainer.offsetHeight;
                startBottomHeight = outputContainer.offsetHeight;
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            
            // Prevent text selection during resize
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'row-resize';
        });

        function onMouseMove(e) {
            if (!isResizing) return;
            
            const container = resizer.parentElement;
            const totalHeight = container.offsetHeight - 6; // Subtract resizer height
            const deltaY = e.clientY - startY;
            
            // Calculate new heights
            let topHeight = startTopHeight + deltaY;
            let bottomHeight = startBottomHeight - deltaY;
            
            // Enforce minimum heights
            const minTopHeight = 200;
            const minBottomHeight = 150;
            
            if (topHeight < minTopHeight) {
                topHeight = minTopHeight;
                bottomHeight = totalHeight - topHeight;
            } else if (bottomHeight < minBottomHeight) {
                bottomHeight = minBottomHeight;
                topHeight = totalHeight - bottomHeight;
            }
            
            // Update flex basis
            const editorContainer = container.querySelector('.editor-container');
            const outputContainer = container.querySelector('.output-container');
            
            if (editorContainer && outputContainer) {
                editorContainer.style.flex = `0 0 ${topHeight}px`;
                outputContainer.style.flex = `0 0 ${bottomHeight}px`;
            }
        }

        function onMouseUp() {
            isResizing = false;
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
        }
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