// static/js/whiteboard_features.js

// این متغیرها به صورت داخلی در ماژول مدیریت می‌شوند و از طریق globalContext پاس داده نمی‌شوند،
// مگر اینکه در globalContext به صورت خاص برای اشتراک با دیگر ماژول‌ها نیاز باشد.
let whiteboardCtx = null;
let whiteboardHistory = []; // تاریخچه برای بازрисовانی و ارسال به کاربران جدید
let isDrawing = false;
let lastX = 0;
let lastY = 0;
let currentTool = 'pencil'; // 'pencil' or 'eraser'
let strokeColor = '#FFFFFF'; // رنگ پیش‌فرض قلم
let lineWidth = 5;       // ضخامت پیش‌فرض قلم

// globalContext شامل مواردی مثل isWhiteboardActive, currentView (برای کنترل امکان رسم),
// chatSocket, currentUserId, reservationId (برای ذخیره), whiteboardCanvas, whiteboardView (برای resize) خواهد بود.

function getRelativeCoords(event, canvas) {
    const rect = canvas.getBoundingClientRect();
    // برای پشتیبانی از لمس و ماوس
    const clientX = event.clientX || (event.touches && event.touches[0].clientX);
    const clientY = event.clientY || (event.touches && event.touches[0].clientY);
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return { x, y };
}

function startDrawWhiteboard(event, globalContext) {
    event.preventDefault(); // جلوگیری از رفتارهای پیش‌فرض مرورگر (مثل اسکرول در لمس)
    // بررسی اینکه آیا وایت‌برد باید فعال باشد و در نمای صحیح هستیم
    if (!globalContext.isWhiteboardActive || globalContext.currentView !== 'whiteboard') return;
    isDrawing = true;
    const { x, y } = getRelativeCoords(event, globalContext.whiteboardCanvas);
    [lastX, lastY] = [x, y];
    // نیازی به beginPath در اینجا نیست، قبل از هر stroke زده می‌شود
}

function drawWhiteboard(event, globalContext) {
    event.preventDefault();
    if (!isDrawing || (!globalContext.isWhiteboardActive || globalContext.currentView !== 'whiteboard')) return;

    const { x, y } = getRelativeCoords(event, globalContext.whiteboardCanvas);
    whiteboardCtx.beginPath(); // شروع مسیر جدید برای هر بخش از رسم
    whiteboardCtx.moveTo(lastX, lastY);
    whiteboardCtx.lineTo(x, y);
    // رنگ پاک‌کن باید رنگ پس‌زمینه وایت‌برد باشد
    whiteboardCtx.strokeStyle = currentTool === 'pencil' ? strokeColor : (globalContext.whiteboardCanvas.style.backgroundColor || '#282b30');
    whiteboardCtx.lineWidth = lineWidth;
    whiteboardCtx.lineCap = 'round'; // برای گوشه‌های گرد در خطوط
    whiteboardCtx.lineJoin = 'round'; // برای اتصال نرم‌تر خطوط
    whiteboardCtx.stroke();

    const drawData = {
        fromX: lastX, fromY: lastY,
        toX: x, toY: y,
        color: whiteboardCtx.strokeStyle, // ارسال رنگ واقعی استفاده شده
        lineWidth: whiteboardCtx.lineWidth,
        tool: currentTool
    };
    whiteboardHistory.push(drawData); // افزودن به تاریخچه محلی

    // ارسال داده‌های رسم به سایر کاربران از طریق WebSocket
    if (globalContext.chatSocket && globalContext.chatSocket.readyState === WebSocket.OPEN) {
        globalContext.chatSocket.send(JSON.stringify({
            type: 'whiteboard_data',
            data: drawData,
            sender_id: globalContext.currentUserId
        }));
    }
    [lastX, lastY] = [x, y]; // آپدیت مختصات قبلی
}

function stopDrawWhiteboard(event) {
    if (event) event.preventDefault(); // اگر event وجود دارد (مثلاً برای mouseup)
    if (!isDrawing) return;
    isDrawing = false;
    // ctx.beginPath(); // برای اطمینان از اینکه رسم بعدی به این نقطه وصل نمی‌شود (اختیاری)
}

function resizeWhiteboardCanvasInternal(canvas, viewContainer) {
    // این تابع باید در globalContext.whiteboardView و globalContext.whiteboardCanvas دسترسی داشته باشد
    if (!canvas || !viewContainer || !whiteboardCtx) return;

    // برای جلوگیری از بازрисовانی‌های غیرضروری اگر ابعاد تغییر نکرده‌اند
    const newWidth = viewContainer.clientWidth > 2 ? viewContainer.clientWidth - 2 : 0; // حداقل عرض ۰
    const newHeight = viewContainer.clientHeight > 2 ? viewContainer.clientHeight - 2 : 0; // حداقل ارتفاع ۰

    if (canvas.width === newWidth && canvas.height === newHeight) {
        return; // ابعاد تغییر نکرده‌اند
    }
    
    if (newWidth > 0 && newHeight > 0) {
        canvas.width = newWidth;
        canvas.height = newHeight;
        redrawWhiteboardHistoryInternal(); // بازрисовانی تاریخچه روی بوم با ابعاد جدید
    } else {
        // اگر ابعاد صفر یا منفی است، بوم را پاک کن
        canvas.width = 0;
        canvas.height = 0;
        whiteboardCtx.clearRect(0,0,canvas.width, canvas.height);
    }
}

function redrawWhiteboardHistoryInternal() {
    if (!whiteboardCtx || !whiteboardCtx.canvas) return;
    // ابتدا بوم را پاک کن
    whiteboardCtx.clearRect(0, 0, whiteboardCtx.canvas.width, whiteboardCtx.canvas.height);
    whiteboardHistory.forEach(data => {
        whiteboardCtx.beginPath();
        whiteboardCtx.moveTo(data.fromX, data.fromY);
        whiteboardCtx.lineTo(data.toX, data.toY);
        whiteboardCtx.strokeStyle = data.color;
        whiteboardCtx.lineWidth = data.lineWidth;
        whiteboardCtx.lineCap = 'round';
        whiteboardCtx.lineJoin = 'round';
        whiteboardCtx.stroke();
    });
}

// تابع اصلی برای مقداردهی اولیه وایت‌برد
export function initWhiteboardFeatures(globalContext) {
    // اطمینان از وجود المان‌های لازم در globalContext
    if (!globalContext.whiteboardCanvas || !globalContext.whiteboardView) {
        console.error("Whiteboard canvas or view container not found in globalContext.");
        return null;
    }
    whiteboardCtx = globalContext.whiteboardCanvas.getContext('2d');
    if (!whiteboardCtx) {
        console.error("Could not get 2D context for whiteboard canvas.");
        return null;
    }

    // یافتن دکمه‌های نوار ابزار از DOM
    const colorPicker = document.getElementById('colorPicker');
    const brushSizeSlider = document.getElementById('brushSize');
    const pencilToolBtn = document.getElementById('pencilTool');
    const eraserToolBtn = document.getElementById('eraserTool');
    const clearBtn = document.getElementById('clearBoardBtn');
    const saveBtn = document.getElementById('saveBoardBtn');

    // تنظیم Event Listener ها برای ابزارهای وایت‌برد
    if (pencilToolBtn) pencilToolBtn.addEventListener('click', () => currentTool = 'pencil');
    if (eraserToolBtn) eraserToolBtn.addEventListener('click', () => currentTool = 'eraser');
    if (colorPicker) colorPicker.addEventListener('change', (e) => strokeColor = e.target.value);
    if (brushSizeSlider) brushSizeSlider.addEventListener('input', (e) => lineWidth = e.target.value);

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (confirm('Clear whiteboard for everyone?')) {
                whiteboardCtx.clearRect(0, 0, globalContext.whiteboardCanvas.width, globalContext.whiteboardCanvas.height);
                whiteboardHistory = []; // پاک کردن تاریخچه محلی
                // ارسال پیام پاک کردن به سایر کاربران
                if (globalContext.chatSocket && globalContext.chatSocket.readyState === WebSocket.OPEN) {
                    globalContext.chatSocket.send(JSON.stringify({
                        type: 'whiteboard_clear',
                        sender_id: globalContext.currentUserId
                    }));
                }
            }
        });
    }

    if (saveBtn) {
        saveBtn.addEventListener('click', () => {
            const dataUrl = globalContext.whiteboardCanvas.toDataURL('image/png');
            const link = document.createElement('a');
            link.href = dataUrl;
            link.download = `whiteboard_${globalContext.reservationId || 'meeting'}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });
    }

    // تنظیم Event Listener ها برای خود بوم نقاشی
    globalContext.whiteboardCanvas.addEventListener('mousedown', (e) => startDrawWhiteboard(e, globalContext));
    globalContext.whiteboardCanvas.addEventListener('mousemove', (e) => drawWhiteboard(e, globalContext));
    globalContext.whiteboardCanvas.addEventListener('mouseup', stopDrawWhiteboard);
    globalContext.whiteboardCanvas.addEventListener('mouseout', stopDrawWhiteboard); // برای زمانی که ماوس از بوم خارج می‌شود

    // پشتیبانی از لمس
    globalContext.whiteboardCanvas.addEventListener('touchstart', (e) => startDrawWhiteboard(e, globalContext), { passive: false });
    globalContext.whiteboardCanvas.addEventListener('touchmove', (e) => drawWhiteboard(e, globalContext), { passive: false });
    globalContext.whiteboardCanvas.addEventListener('touchend', stopDrawWhiteboard, { passive: false });
    globalContext.whiteboardCanvas.addEventListener('touchcancel', stopDrawWhiteboard, { passive: false });


    // آبجکتی که توابع قابل دسترسی از خارج ماژول را برمی‌گرداند
    const externalHandler = {
        resizeCanvas: () => resizeWhiteboardCanvasInternal(globalContext.whiteboardCanvas, globalContext.whiteboardView),
        redrawHistory: redrawWhiteboardHistoryInternal,
        getHistory: () => whiteboardHistory, // برای ارسال تاریخچه به کاربران جدید
        // توابع برای مدیریت داده‌های دریافتی از WebSocket
        handleDrawEvent: (data) => {
            if (!whiteboardCtx || (data.sender_id === globalContext.currentUserId)) return; // داده خودمان را دوباره رسم نکنیم
            whiteboardCtx.beginPath();
            whiteboardCtx.moveTo(data.fromX, data.fromY);
            whiteboardCtx.lineTo(data.toX, data.toY);
            whiteboardCtx.strokeStyle = data.color;
            whiteboardCtx.lineWidth = data.lineWidth;
            whiteboardCtx.lineCap = 'round';
            whiteboardCtx.lineJoin = 'round';
            whiteboardCtx.stroke();
            whiteboardHistory.push(data); // افزودن به تاریخچه برای هماهنگی
        },
        handleClearEvent: (data) => {
             if (!whiteboardCtx || (data && data.sender_id === globalContext.currentUserId && !confirm("You initiated the clear action on another device. Clear here too?"))) return;
            whiteboardCtx.clearRect(0, 0, globalContext.whiteboardCanvas.width, globalContext.whiteboardCanvas.height);
            whiteboardHistory = [];
        },
        applyHistory: (historyData) => {
            if (!Array.isArray(historyData)) {
                console.warn("Received invalid history data for whiteboard.");
                historyData = [];
            }
            whiteboardHistory = historyData; // جایگزینی تاریخچه محلی با تاریخچه دریافتی
            redrawWhiteboardHistoryInternal();
        }
    };

    // تغییر اندازه اولیه بوم و تنظیم شنونده برای تغییر اندازه پنجره
    // با کمی تاخیر اجرا شود تا ابعاد والد به درستی محاسبه شده باشند
    setTimeout(() => externalHandler.resizeCanvas(), 100);
    window.addEventListener('resize', () => externalHandler.resizeCanvas());

    return externalHandler;
}