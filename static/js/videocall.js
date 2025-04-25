class VideoCall {
    constructor(reservationId, currentUserId) {
        this.reservationId = reservationId;
        this.currentUserId = currentUserId;
        this.localStream = null;
        this.peerConnections = {};
        this.socket = null;
        this.localVideo = document.getElementById('localVideo');
        this.remoteVideosContainer = document.getElementById('remoteVideos');
        this.startCallBtn = document.getElementById('startCall');
        this.stopCallBtn = document.getElementById('endCall');
        
        this.iceServers = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };
        
        this.setupEventListeners();
        this.connectWebSocket();
    }
    
    setupEventListeners() {
        this.startCallBtn.addEventListener('click', () => this.startCall());
        this.stopCallBtn.addEventListener('click', () => this.endCall());
    }
    
    connectWebSocket() {
        this.socket = new WebSocket(`ws://${window.location.host}/ws/webrtc/${this.reservationId}/`);
        
        this.socket.onopen = () => {
            console.log('WebRTC WebSocket connection established');
        };
        
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch (data.type) {
                case 'user_connected':
                    console.log(`User connected: ${data.username}`);
                    if (this.localStream && data.user_id !== this.currentUserId) {
                        this.createPeerConnection(data.user_id);
                        this.createOffer(data.user_id);
                    }
                    break;
                    
                case 'user_disconnected':
                    console.log(`User disconnected: ${data.username}`);
                    this.removePeerConnection(data.user_id);
                    break;
                    
                case 'offer':
                    if (data.receiver_id === this.currentUserId) {
                        this.handleOffer(data.offer, data.sender_id);
                    }
                    break;
                    
                case 'answer':
                    if (data.receiver_id === this.currentUserId) {
                        this.handleAnswer(data.answer, data.sender_id);
                    }
                    break;
                    
                case 'ice_candidate':
                    if (data.receiver_id === this.currentUserId) {
                        this.handleIceCandidate(data.candidate, data.sender_id);
                    }
                    break;
            }
        };
        
        this.socket.onclose = () => {
            console.log('WebRTC WebSocket connection closed');
        };
        
        this.socket.onerror = (error) => {
            console.error('WebRTC WebSocket error:', error);
        };
    }
    
    async startCall() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });
            
            this.localVideo.srcObject = this.localStream;
            this.startCallBtn.style.display = 'none';
            this.stopCallBtn.style.display = 'inline-block';
            document.getElementById('videoCallControls').style.display = 'flex';
            
            // Create peer connections with all existing participants
            const participantsEl = document.getElementById('participantsList');
            if (participantsEl) {
                const participants = JSON.parse(participantsEl.dataset.participants);
                participants.forEach(participant => {
                    if (participant.userId !== this.currentUserId) {
                        this.createPeerConnection(participant.userId);
                        this.createOffer(participant.userId);
                    }
                });
            }
        } catch (error) {
            console.error('Error accessing media devices:', error);
            alert('Unable to access camera and microphone. Please ensure permissions are granted.');
        }
    }
    
    endCall() {
        // Stop all tracks in local stream
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        // Close all peer connections
        Object.keys(this.peerConnections).forEach(userId => {
            this.removePeerConnection(userId);
        });
        
        // Clear video elements
        this.localVideo.srcObject = null;
        this.remoteVideosContainer.innerHTML = '';
        
        // Show/hide buttons
        this.startCallBtn.style.display = 'inline-block';
        this.stopCallBtn.style.display = 'none';
        document.getElementById('videoCallControls').style.display = 'none';
    }
    
    createPeerConnection(userId) {
        if (this.peerConnections[userId]) {
            console.log(`Peer connection with ${userId} already exists`);
            return;
        }
        
        const peerConnection = new RTCPeerConnection(this.iceServers);
        this.peerConnections[userId] = peerConnection;
        
        // Add local tracks to the peer connection
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                peerConnection.addTrack(track, this.localStream);
            });
        }
        
        // Set up ice candidate handler
        peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.socket.send(JSON.stringify({
                    type: 'ice_candidate',
                    candidate: event.candidate,
                    receiver_id: userId
                }));
            }
        };
        
        // Set up track handler for remote streams
        peerConnection.ontrack = (event) => {
            if (!document.getElementById(`remoteVideo-${userId}`)) {
                const remoteVideo = document.createElement('video');
                remoteVideo.id = `remoteVideo-${userId}`;
                remoteVideo.autoplay = true;
                remoteVideo.playsInline = true;
                remoteVideo.className = 'remote-video';
                this.remoteVideosContainer.appendChild(remoteVideo);
            }
            
            const remoteVideo = document.getElementById(`remoteVideo-${userId}`);
            remoteVideo.srcObject = event.streams[0];
        };
        
        console.log(`Created peer connection for user ${userId}`);
        return peerConnection;
    }
    
    async createOffer(userId) {
        const peerConnection = this.peerConnections[userId] || this.createPeerConnection(userId);
        
        try {
            const offer = await peerConnection.createOffer({
                offerToReceiveAudio: true,
                offerToReceiveVideo: true
            });
            
            await peerConnection.setLocalDescription(offer);
            
            this.socket.send(JSON.stringify({
                type: 'offer',
                offer: offer,
                receiver_id: userId
            }));
            
            console.log(`Sent offer to user ${userId}`);
        } catch (error) {
            console.error('Error creating offer:', error);
        }
    }
    
    async handleOffer(offer, senderId) {
        // Create peer connection if it doesn't exist
        const peerConnection = this.peerConnections[senderId] || this.createPeerConnection(senderId);
        
        try {
            await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
            
            // Create answer
            const answer = await peerConnection.createAnswer();
            await peerConnection.setLocalDescription(answer);
            
            this.socket.send(JSON.stringify({
                type: 'answer',
                answer: answer,
                receiver_id: senderId
            }));
            
            console.log(`Sent answer to user ${senderId}`);
        } catch (error) {
            console.error('Error handling offer:', error);
        }
    }
    
    async handleAnswer(answer, senderId) {
        const peerConnection = this.peerConnections[senderId];
        
        if (peerConnection) {
            try {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
                console.log(`Applied answer from user ${senderId}`);
            } catch (error) {
                console.error('Error handling answer:', error);
            }
        }
    }
    
    async handleIceCandidate(candidate, senderId) {
        const peerConnection = this.peerConnections[senderId];
        
        if (peerConnection) {
            try {
                await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
                console.log(`Added ICE candidate from user ${senderId}`);
            } catch (error) {
                console.error('Error adding ICE candidate:', error);
            }
        }
    }
    
    removePeerConnection(userId) {
        const peerConnection = this.peerConnections[userId];
        
        if (peerConnection) {
            peerConnection.close();
            delete this.peerConnections[userId];
            console.log(`Removed peer connection for user ${userId}`);
        }
        
        // Remove remote video element
        const remoteVideo = document.getElementById(`remoteVideo-${userId}`);
        if (remoteVideo) {
            remoteVideo.srcObject = null;
            remoteVideo.remove();
        }
    }
    
    // Toggle camera
    toggleCamera() {
        if (!this.localStream) return;
        
        const videoTrack = this.localStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.enabled = !videoTrack.enabled;
            return videoTrack.enabled;
        }
        return false;
    }
    
    // Toggle microphone
    toggleMicrophone() {
        if (!this.localStream) return;
        
        const audioTrack = this.localStream.getAudioTracks()[0];
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled;
            return audioTrack.enabled;
        }
        return false;
    }
}

// Initialize the video call when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const reservationId = document.getElementById('videocall-container').dataset.reservationId;
    const currentUserId = document.getElementById('videocall-container').dataset.currentUserId;
    
    window.videoCall = new VideoCall(reservationId, currentUserId);
    
    // Setup toggle buttons
    document.getElementById('toggleCamera').addEventListener('click', (e) => {
        const isEnabled = window.videoCall.toggleCamera();
        e.target.innerHTML = isEnabled ? '<i class="fas fa-video"></i>' : '<i class="fas fa-video-slash"></i>';
    });
    
    document.getElementById('toggleMic').addEventListener('click', (e) => {
        const isEnabled = window.videoCall.toggleMicrophone();
        e.target.innerHTML = isEnabled ? '<i class="fas fa-microphone"></i>' : '<i class="fas fa-microphone-slash"></i>';
    });
});