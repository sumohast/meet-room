// static/js/videocall_features.js

function createPeerConnectionForVideo(peerId, peerUsername, globalContext) {
    if (globalContext.peerConnections[peerId]) {
        console.warn(`Peer connection for ${peerId} already exists.`);
        return globalContext.peerConnections[peerId];
    }

    console.log(`Creating new peer connection for: ${peerId} (${peerUsername})`);
    const pc = new RTCPeerConnection({ iceServers: globalContext.ICE_SERVERS });
    globalContext.peerConnections[peerId] = pc;

    pc.onicecandidate = (event) => {
        if (event.candidate && globalContext.chatSocket && globalContext.chatSocket.readyState === WebSocket.OPEN) {
            globalContext.chatSocket.send(JSON.stringify({
                type: 'ice_candidate', // این نوع پیام باید توسط Consumer مناسب در بک‌اند مدیریت شود
                candidate: event.candidate,
                recipient_id: peerId,
                sender_id: globalContext.currentUserId
            }));
        }
    };

    pc.ontrack = (event) => {
        console.log(`Track received from ${peerId}`, event.track, event.streams);
        let remoteVideoContainerEl = document.getElementById(`remote-video-container-${peerId}`);

        if (!remoteVideoContainerEl) {
            remoteVideoContainerEl = document.createElement('div');
            remoteVideoContainerEl.className = 'remote-video-container';
            remoteVideoContainerEl.id = `remote-video-container-${peerId}`;

            const videoEl = document.createElement('video');
            videoEl.id = `remote-video-${peerId}`;
            videoEl.autoplay = true;
            videoEl.playsInline = true;

            const labelEl = document.createElement('div');
            labelEl.className = 'video-label-remote';
            // استفاده از globalContext.participants برای گرفتن نام کاربر
            labelEl.textContent = peerUsername || globalContext.participants.get(peerId) || 'Remote User';

            remoteVideoContainerEl.appendChild(videoEl);
            remoteVideoContainerEl.appendChild(labelEl);
            globalContext.remoteVideosContainer.appendChild(remoteVideoContainerEl);
        }

        const videoElement = document.getElementById(`remote-video-${peerId}`);
        if (event.streams && event.streams[0]) {
            videoElement.srcObject = event.streams[0];
        } else {
            let inboundStream = new MediaStream();
            inboundStream.addTrack(event.track);
            videoElement.srcObject = inboundStream;
        }
    };

    pc.oniceconnectionstatechange = () => {
        console.log(`ICE connection state for ${peerId}: ${pc.iceConnectionState}`);
        if (pc.iceConnectionState === 'failed' || pc.iceConnectionState === 'disconnected' || pc.iceConnectionState === 'closed') {
            const remoteVideoContainerToRemove = document.getElementById(`remote-video-container-${peerId}`);
            if (remoteVideoContainerToRemove) remoteVideoContainerToRemove.remove();
            delete globalContext.peerConnections[peerId];
            // ممکن است بخواهید کاربر را از لیست participants هم حذف کنید اگر WebSocket هم قطع شده باشد
        }
    };

    // Add local stream tracks
    if (globalContext.localStream) {
        globalContext.localStream.getTracks().forEach(track => {
            try {
                pc.addTrack(track, globalContext.localStream);
            } catch (e) {
                console.error("Error adding track to PC:", e);
            }
        });
    } else {
        console.warn("Local stream not available when creating peer connection for", peerId);
    }

    // Add pending ICE candidates
    if (globalContext.pendingIceCandidatesForPeer[peerId]) {
        globalContext.pendingIceCandidatesForPeer[peerId].forEach(candidate => {
            pc.addIceCandidate(new RTCIceCandidate(candidate))
              .catch(e => console.error("Error adding pending ICE candidate:", e));
        });
        delete globalContext.pendingIceCandidatesForPeer[peerId];
    }
    return pc;
}

async function handleOfferForVideo(offer, senderId, globalContext) {
    // استفاده از globalContext.participants برای گرفتن نام کاربر
    const senderUsername = globalContext.participants.get(senderId) || "A user";
    console.log(`Received offer from ${senderId} (${senderUsername})`);

    // پاس دادن کل globalContext به createPeerConnectionForVideo
    const pc = globalContext.peerConnections[senderId] || createPeerConnectionForVideo(senderId, senderUsername, globalContext);
    if (!pc) return;

    try {
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        if (globalContext.chatSocket && globalContext.chatSocket.readyState === WebSocket.OPEN) {
            globalContext.chatSocket.send(JSON.stringify({
                type: 'answer', // این نوع پیام باید توسط Consumer مناسب در بک‌اند مدیریت شود
                answer: pc.localDescription,
                recipient_id: senderId,
                sender_id: globalContext.currentUserId
            }));
        }
    } catch (e) {
        console.error("Error handling offer:", e);
    }
}

async function handleAnswerForVideo(answer, senderId, globalContext) {
    console.log(`Received answer from ${senderId}`);
    const pc = globalContext.peerConnections[senderId];
    if (pc) {
        try {
            await pc.setRemoteDescription(new RTCSessionDescription(answer));
        } catch (e) {
            console.error("Error handling answer:", e);
        }
    }
}

async function handleIceCandidateForVideo(candidate, senderId, globalContext) {
    // console.log(`Received ICE candidate from ${senderId}`); // برای جلوگیری از لاگ زیاد می‌توان کامنت کرد
    const pc = globalContext.peerConnections[senderId];
    if (pc) {
        if (pc.remoteDescription) { // Only add candidate if remote description is set
            try {
                await pc.addIceCandidate(new RTCIceCandidate(candidate));
            } catch (e) {
                console.error("Error adding received ICE candidate:", e);
            }
        } else { // Buffer candidate if remote description isn't set yet
            if (!globalContext.pendingIceCandidatesForPeer[senderId]) {
                globalContext.pendingIceCandidatesForPeer[senderId] = [];
            }
            globalContext.pendingIceCandidatesForPeer[senderId].push(candidate);
            console.log(`Buffered ICE candidate from ${senderId} because remote description is not set.`);
        }
    } else {
         console.warn(`No peer connection for ${senderId} to add ICE candidate. Buffering.`);
          if (!globalContext.pendingIceCandidatesForPeer[senderId]) {
              globalContext.pendingIceCandidatesForPeer[senderId] = [];
          }
          globalContext.pendingIceCandidatesForPeer[senderId].push(candidate);
    }
}

// تابع init که از فایل اصلی صدا زده می‌شود
// و توابع مورد نیاز برای هندل کردن رویدادهای WebSocket را برمی‌گرداند
export function initVideoCallFeatures(passedGlobalContext) {
    // اطمینان از اینکه تمام موارد لازم در passedGlobalContext وجود دارند
    const requiredKeys = [
        'chatSocket', 'currentUserId', 'localStream', 'ICE_SERVERS',
        'peerConnections', 'pendingIceCandidatesForPeer',
        'remoteVideosContainer', 'participants'
    ];
    for (const key of requiredKeys) {
        if (!(key in passedGlobalContext)) {
            console.error(`VideoCallFeatures Init Error: Missing '${key}' in globalContext.`);
            // return null; // یا یک آبجکت خالی یا throw error
        }
    }
    
    return {
        createPeerConnection: (peerId, peerUsername) => createPeerConnectionForVideo(peerId, peerUsername, passedGlobalContext),
        handleOffer: (offer, senderId) => handleOfferForVideo(offer, senderId, passedGlobalContext),
        handleAnswer: (answer, senderId) => handleAnswerForVideo(answer, senderId, passedGlobalContext),
        handleIceCandidate: (candidate, senderId) => handleIceCandidateForVideo(candidate, senderId, passedGlobalContext),
        // تابعی برای پاکسازی یک کاربر خاص در صورت user_leave از وب‌سوکت
        removePeer: (peerId) => {
            if (passedGlobalContext.peerConnections[peerId]) {
                passedGlobalContext.peerConnections[peerId].close();
                delete passedGlobalContext.peerConnections[peerId];
            }
            const remoteVideoContainerToRemove = document.getElementById(`remote-video-container-${peerId}`);
            if (remoteVideoContainerToRemove) remoteVideoContainerToRemove.remove();
        }
    };
}