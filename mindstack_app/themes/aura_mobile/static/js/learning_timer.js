
/**
 * LearningTimer - Quản lý thời gian học tập chủ động
 * Chống AFK dựa trên tương tác thực tế (chuột, phím, chạm)
 */
class LearningTimer {
    constructor(idleThresholdMs = 20000) {
        this.idleThresholdMs = idleThresholdMs;
        this.reset();
        
        // Các sự kiện đánh dấu user đang hoạt động
        this.activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
        this.boundRecordActivity = this.recordActivity.bind(this);
    }

    reset() {
        this.startTime = Date.now();
        this.lastActivityTime = Date.now();
        this.totalIdleTimeMs = 0;
        this.isIdle = false;
        this.isRunning = false;
    }

    start() {
        this.reset();
        this.isRunning = true;
        this.activityEvents.forEach(event => {
            window.addEventListener(event, this.boundRecordActivity, { passive: true });
        });
        
        // Kiểm tra trạng thái Idle mỗi giây
        this.idleCheckInterval = setInterval(() => this.checkIdle(), 1000);
    }

    stop() {
        this.isRunning = false;
        clearInterval(this.idleCheckInterval);
        this.activityEvents.forEach(event => {
            window.removeEventListener(event, this.boundRecordActivity);
        });
    }

    recordActivity() {
        const now = Date.now();
        
        // Nếu đang Idle mà có hành động -> Kết thúc thời gian Idle
        if (this.isIdle) {
            const idleDuration = now - this.lastActivityTime;
            this.totalIdleTimeMs += idleDuration;
            this.isIdle = false;
            // console.log(`[Timer] Resume from idle. Idle duration: ${idleDuration}ms`);
        }
        
        this.lastActivityTime = now;
    }

    checkIdle() {
        if (!this.isRunning || this.isIdle) return;

        const now = Date.now();
        if (now - this.lastActivityTime > this.idleThresholdMs) {
            this.isIdle = true;
            // console.log("[Timer] User is now IDLE (AFK detected)");
        }
    }

    getDuration() {
        if (!this.startTime) return 0;
        
        const now = Date.now();
        let totalElapsed = now - this.startTime;
        
        // Nếu đang kết thúc ở trạng thái Idle, trừ đi phần thời gian Idle cuối cùng
        let currentIdleBonus = 0;
        if (this.isIdle) {
            currentIdleBonus = now - this.lastActivityTime;
        }
        
        const activeDuration = totalElapsed - this.totalIdleTimeMs - currentIdleBonus;
        return Math.max(0, activeDuration);
    }
}

// Khởi tạo global instance
window.learningTimer = new LearningTimer();
