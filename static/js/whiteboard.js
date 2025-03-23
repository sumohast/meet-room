class Whiteboard {
    constructor() {
        this.canvas = document.getElementById('whiteboard');
        this.ctx = this.canvas.getContext('2d');
        this.isDrawing = false;
        this.currentTool = 'pencil';
        this.socket = new WebSocket(
            `ws://${window.location.host}/ws/whiteboard/${ROOM_ID}/`
        );
        
        this.initializeCanvas();
        this.setupEventListeners();
        this.setupWebSocket();
    }

    initializeCanvas() {
        this.canvas.width = this.canvas.parentElement.offsetWidth;
        this.canvas.height = window.innerHeight * 0.7;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';
    }

    setupEventListeners() {
        this.canvas.addEventListener('mousedown', this.startDrawing.bind(this));
        this.canvas.addEventListener('mousemove', this.draw.bind(this));
        this.canvas.addEventListener('mouseup', this.stopDrawing.bind(this));
        this.canvas.addEventListener('mouseout', this.stopDrawing.bind(this));
        
        document.getElementById('pencilTool').onclick = () => this.currentTool = 'pencil';
        document.getElementById('eraserTool').onclick = () => this.currentTool = 'eraser';
        document.getElementById('clearBoard').onclick = () => this.clearCanvas();
        document.getElementById('saveBoard').onclick = () => this.saveCanvas();
    }

    setupWebSocket() {
        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'draw') {
                this.drawFromWebSocket(data);
            }
        };
    }

    startDrawing(e) {
        this.isDrawing = true;
        const pos = this.getMousePos(e);
        this.ctx.beginPath();
        this.ctx.moveTo(pos.x, pos.y);
    }

    draw(e) {
        if (!this.isDrawing) return;
        
        const pos = this.getMousePos(e);
        this.ctx.lineWidth = document.getElementById('brushSize').value;
        this.ctx.strokeStyle = this.currentTool === 'eraser' ? '#fff' : 
                              document.getElementById('colorPicker').value;
        
        this.ctx.lineTo(pos.x, pos.y);
        this.ctx.stroke();
        
        this.sendDrawData({
            x: pos.x,
            y: pos.y,
            tool: this.currentTool,
            color: this.ctx.strokeStyle,
            width: this.ctx.lineWidth
        });
    }

    stopDrawing() {
        this.isDrawing = false;
        this.ctx.beginPath();
    }

    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    sendDrawData(data) {
        this.socket.send(JSON.stringify({
            type: 'draw',
            data: data
        }));
    }

    drawFromWebSocket(data) {
        this.ctx.lineWidth = data.width;
        this.ctx.strokeStyle = data.color;
        this.ctx.lineTo(data.x, data.y);
        this.ctx.stroke();
    }

    clearCanvas() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.socket.send(JSON.stringify({type: 'clear'}));
    }

    saveCanvas() {
        const dataURL = this.canvas.toDataURL();
        fetch('/api/whiteboard-update/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                room_id: ROOM_ID,
                data: dataURL
            })
        });
    }
}

const whiteboard = new Whiteboard();