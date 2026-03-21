
/**
 * LearningTimer - Quản lý thời gian học tập chủ động
 * Chống AFK dựa trên tương tác thực tế (chuột, phím, chạm)
 * Hỗ trợ tự động dừng khi mất tiêu điểm cửa sổ hoặc ẩn tab.
 */
class LearningTimer {
    constructor(idleThresholdMs = 20000) {
        this.idleThresholdMs = idleThresholdMs;
        this.reset();
        
        this.activityEvents = ['mousemove', 'keydown', 'click', 'scroll', 'touchstart'];
        this.boundRecordActivity = this.recordActivity.bind(this);
        
        this.boundHandleInactive = this.handleInactive.bind(this);
        this.boundHandleActive = this.handleActive.bind(this);
        this.boundVisibilityChange = this.onVisibilityChange.bind(this);
    }

    reset() {
        this.startTime = Date.now();
        this.lastActivityTime = Date.now();
        this.totalIdleTimeMs = 0;
        this.isIdle = false;
        this.isRunning = false;
        this.savedDuration = 0;
        this.isDocumentHidden = false;
        this.hiddenStartTime = 0;
    }

    start() {
        this.reset();
        this.isRunning = true;
        this.activityEvents.forEach(event => {
            window.addEventListener(event, this.boundRecordActivity, { passive: true });
        });
        
        document.addEventListener('visibilitychange', this.boundVisibilityChange);
        window.addEventListener('blur', this.boundHandleInactive);
        window.addEventListener('focus', this.boundHandleActive);

        this.idleCheckInterval = setInterval(() => this.checkIdle(), 1000);
        console.log("[Timer] Started.");
    }

    stop() {
        if (this.isRunning) {
            this.savedDuration = this.getDuration();
        }
        this.isRunning = false;
        clearInterval(this.idleCheckInterval);
        this.activityEvents.forEach(event => {
            window.removeEventListener(event, this.boundRecordActivity);
        });
        document.removeEventListener('visibilitychange', this.boundVisibilityChange);
        window.removeEventListener('blur', this.boundHandleInactive);
        window.removeEventListener('focus', this.boundHandleActive);
        console.log("[Timer] Stopped.");
    }

    recordActivity() {
        if (!this.isRunning || this.isDocumentHidden) return;
        
        const now = Date.now();
        if (this.isIdle) {
            const totalGap = now - this.lastActivityTime;
            const gracePeriodMs = 10000;
            const idleToSubtract = Math.max(0, totalGap - gracePeriodMs);
            this.totalIdleTimeMs += idleToSubtract;
            this.isIdle = false;
            console.log(`[Timer] Interaction detected. Subtracted AFK: ${idleToSubtract}ms`);
        }
        this.lastActivityTime = now;
    }

    checkIdle() {
        if (!this.isRunning || this.isIdle || this.isDocumentHidden) return;

        const now = Date.now();
        if (now - this.lastActivityTime > this.idleThresholdMs) {
            this.isIdle = true;
            console.log("[Timer] User is now IDLE (AFK)");
        }
    }

    onVisibilityChange() {
        if (document.hidden) {
            this.handleInactive();
        } else {
            this.handleActive();
        }
    }

    handleInactive() {
        if (!this.isRunning || this.isDocumentHidden) return;
        
        this.isDocumentHidden = true;
        this.hiddenStartTime = Date.now();
        this.isIdle = true;
        console.log(`[Timer] Paused (Window/Tab inactive) at: ${this.getFormattedDuration()}`);
    }

    handleActive() {
        if (!this.isRunning || !this.isDocumentHidden) return;
        
        // Ensure we only resume if the page is actually visible AND focused
        if (!document.hidden && document.hasFocus()) {
            const now = Date.now();
            const hiddenDuration = now - this.hiddenStartTime;
            this.totalIdleTimeMs += hiddenDuration;
            this.isDocumentHidden = false;
            
            this.lastActivityTime = now;
            this.recordActivity();
            console.log(`[Timer] Resumed after ${hiddenDuration}ms. Total Idle: ${this.totalIdleTimeMs}ms`);
        }
    }

    getDuration() {
        if (!this.isRunning && this.startTime) {
            return this.savedDuration || 0;
        }
        if (!this.startTime) return 0;
        
        const now = Date.now();
        const totalElapsed = now - this.startTime;
        
        let currentHiddenSubtract = 0;
        if (this.isDocumentHidden) {
            currentHiddenSubtract = now - this.hiddenStartTime;
        }

        let currentIdleSubtract = 0;
        if (this.isIdle && !this.isDocumentHidden) {
            const currentGap = now - this.lastActivityTime;
            const gracePeriodMs = 10000;
            currentIdleSubtract = Math.max(0, currentGap - gracePeriodMs);
        }
        
        const activeDuration = totalElapsed - this.totalIdleTimeMs - currentHiddenSubtract - currentIdleSubtract;
        return Math.max(0, activeDuration);
    }

    getFormattedDuration() {
        const ms = this.getDuration();
        const sc = Math.floor(ms / 1000);
        const m = Math.floor(sc / 60);
        const s = sc % 60;
        return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
}

window.learningTimer = new LearningTimer();
