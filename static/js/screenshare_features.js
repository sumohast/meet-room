// static/js/screenshare_features.js

function startScreenSharing(globalContext) {
    return async () => {
        if (globalContext.isScreenSharing) return;
        try {
            const screenStream = await navigator.mediaDevices.getDisplayMedia({ 
                video: true, 
                audio: { echoCancellation: true, noiseSuppression: true } 
            });
            
            globalContext.screenStream = screenStream;
            globalContext.isScreenSharing = true;
            globalContext.screenShareVideoEl.srcObject = screenStream;
            globalContext.showView('screenshare');
            globalContext.startShareBtn.style.display = 'none';
            globalContext.stopShareBtn.style.display = 'inline-flex';
            
            if (globalContext.toggleWhiteboardBtn) {
                globalContext.toggleWhiteboardBtn.classList.remove('active');
            }
            if (typeof globalContext.setWhiteboardActiveState === 'function') {
                globalContext.setWhiteboardActiveState(false);
            }

            // Replace video track in all peer connections
            Object.values(globalContext.peerConnections).forEach(pc => {
                const sender = pc.getSenders().find(s => s.track && s.track.kind === 'video');
                if (sender && screenStream.getVideoTracks().length > 0) {
                    sender.replaceTrack(screenStream.getVideoTracks()[0])
                        .catch(e => console.error("Error replacing track with screen:", e));
                } else if (screenStream.getVideoTracks().length > 0) {
                    screenStream.getTracks().forEach(track => {
                        try {
                            pc.addTrack(track, screenStream);
                        } catch (e) {
                            console.error("Error adding screen track:", e);
                        }
                    });
                }
            });

            // Listen for screen share end
            screenStream.getVideoTracks()[0].addEventListener('ended', () => {
                stopScreenSharing(false, globalContext);
            });

            // Notify other users
            if (globalContext.chatSocket && globalContext.chatSocket.readyState === WebSocket.OPEN) {
                globalContext.chatSocket.send(JSON.stringify({ 
                    type: 'start_screen_share', 
                    user_id: globalContext.currentUserId, 
                    username: globalContext.currentUsername 
                }));
            }

        } catch (err) {
            console.error("Error starting screen share:", err);
            globalContext.isScreenSharing = false;
        }
    };
}

function stopScreenSharing(notifyServer = true, globalContext) {
    if (!globalContext.isScreenSharing || !globalContext.screenStream) return;

    // Replace screen track back to camera
    if (globalContext.localStream && globalContext.localStream.getVideoTracks().length > 0) {
        const cameraTrack = globalContext.localStream.getVideoTracks()[0];
        Object.values(globalContext.peerConnections).forEach(pc => {
            const sender = pc.getSenders().find(s => s.track && s.track.kind === 'video');
            if (sender) {
                sender.replaceTrack(cameraTrack)
                    .catch(e => console.error("Error replacing track back to camera:", e));
            }
        });
    }

    // Stop screen stream
    globalContext.screenStream.getTracks().forEach(track => track.stop());
    globalContext.screenStream = null;
    globalContext.isScreenSharing = false;
    globalContext.screenShareVideoEl.srcObject = null;
    globalContext.showView('video');
    globalContext.startShareBtn.style.display = 'inline-flex';
    globalContext.stopShareBtn.style.display = 'none';

    // Notify server
    if (notifyServer && globalContext.chatSocket && globalContext.chatSocket.readyState === WebSocket.OPEN) {
        globalContext.chatSocket.send(JSON.stringify({ 
            type: 'stop_screen_share', 
            user_id: globalContext.currentUserId, 
            username: globalContext.currentUsername 
        }));
    }
}

export function initScreenShareFeatures(globalContext) {
    // Add event listeners
    globalContext.startShareBtn.addEventListener('click', startScreenSharing(globalContext));
    globalContext.stopShareBtn.addEventListener('click', () => stopScreenSharing(true, globalContext));
    
    // Return control methods
    return {
        isCurrentlySharing: () => globalContext.isScreenSharing,
        stopSharing: (notify = true) => stopScreenSharing(notify, globalContext)
    };
}