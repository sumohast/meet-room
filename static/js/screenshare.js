class ScreenShare {
    constructor() {
        this.video = document.getElementById('screenShareVideo');
        this.startBtn = document.getElementById('startShare');
        this.stopBtn = document.getElementById('stopShare');
        this.stream = null;
        
        this.setupEventListeners();
    }

    setupEventListeners() {
        this.startBtn.addEventListener('click', () => this.startSharing());
        this.stopBtn.addEventListener('click', () => this.stopSharing());
    }

    async startSharing() {
        try {
            this.stream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    cursor: "always"
                },
                audio: false
            });

            this.video.srcObject = this.stream;
            this.video.style.display = 'block';
            this.startBtn.style.display = 'none';
            this.stopBtn.style.display = 'inline-block';

            this.stream.getVideoTracks()[0].onended = () => {
                this.stopSharing();
            };
        } catch (err) {
            console.error('Error sharing screen:', err);
            alert('Unable to share screen. Please try again.');
        }
    }

    stopSharing() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        this.video.style.display = 'none';
        this.startBtn.style.display = 'inline-block';
        this.stopBtn.style.display = 'none';
    }
}

const screenShare = new ScreenShare();