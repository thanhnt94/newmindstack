
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
            // Khi bị coi là AFK, chúng ta chỉ "tặng" cho user 10s thời gian suy nghĩ (grace period)
            // Thay vì lấy toàn bộ 20s threshold.
            const totalGap = now - this.lastActivityTime;
            const gracePeriodMs = 10000; // 10 giây
            
            // Thời gian Idle thực sự cần trừ đi = Tổng khoảng trống - 10s được tặng
            const idleToSubtract = Math.max(0, totalGap - gracePeriodMs);
            this.totalIdleTimeMs += idleToSubtract;
            
            this.isIdle = false;
            // console.log(`[Timer] Resume from idle. Subtracted AFK: ${idleToSubtract}ms`);
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
        
        // Nếu đang ở trạng thái Idle, chúng ta cũng chỉ tính 10s hoạt động từ lúc activity cuối
        let currentIdleSubtract = 0;
        if (this.isIdle) {
            const currentGap = now - this.lastActivityTime;
            const gracePeriodMs = 10000;
            currentIdleSubtract = Math.max(0, currentGap - gracePeriodMs);
        }
        
        const activeDuration = totalElapsed - this.totalIdleTimeMs - currentIdleSubtract;
        return Math.max(0, activeDuration);
    }

    getFormattedDuration() {
        const ms = this.getDuration();
        const totalSeconds = Math.floor(ms / 1000);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

// Khởi tạo global instance
window.learningTimer = new LearningTimer();
