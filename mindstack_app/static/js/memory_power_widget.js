// Memory Power Widget - Displays mastery, retention, and memory power metrics
// Usage: Include in flashcard session templates and call updateMemoryPower() after each answer

class MemoryPowerWidget {
    constructor(containerId = 'memory-power-widget') {
        this.container = document.getElementById(containerId);
        this.isVisible = false;
        this.init();
    }

    init() {
        if (!this.container) {
            console.warn('Memory Power Widget container not found');
            return;
        }
    }

    /**
     * Update widget with new Memory Power data
     * @param {Object} data - Memory Power data from backend
     * @param {number} data.mastery - Mastery percentage (0-100)
     * @param {number} data.retention - Retention percentage (0-100)
     * @param {number} data.memory_power - Overall memory power (0-100)
     * @param {number} data.correct_streak - Current correct streak
     * @param {number} data.incorrect_streak - Current incorrect streak
     * @param {string} data.next_review - ISO timestamp of next review
     */
    update(data) {
        if (!data) {
            this.hide();
            return;
        }

        const mastery = data.mastery || 0;
        const retention = data.retention || 0;
        const memoryPower = data.memory_power || 0;
        const correctStreak = data.correct_streak || 0;
        const nextReview = data.next_review;

        // Update main Memory Power display
        const mpElement = this.container.querySelector('.mp-value');
        if (mpElement) {
            mpElement.textContent = `${memoryPower.toFixed(1)}%`;
            mpElement.className = `mp-value ${this.getColorClass(memoryPower)}`;
        }

        // Update mastery bar
        this.updateProgressBar('mastery', mastery);

        // Update retention bar
        this.updateProgressBar('retention', retention);

        // Update streak display
        const streakElement = this.container.querySelector('.mp-streak');
        if (streakElement && correctStreak > 0) {
            streakElement.textContent = `🔥 ${correctStreak} correct`;
            streakElement.style.display = 'block';
        }

        // Update next review time
        if (nextReview) {
            this.updateNextReview(nextReview);
        }

        // Animate update
        this.container.classList.add('mp-updated');
        setTimeout(() => {
            this.container.classList.remove('mp-updated');
        }, 500);

        this.show();
    }

    updateProgressBar(type, percentage) {
        const bar = this.container.querySelector(`.mp-bar-${type}`);
        const label = this.container.querySelector(`.mp-label-${type}`);

        if (bar) {
            bar.style.width = `${percentage}%`;
            bar.className = `mp-bar mp-bar-${type} ${this.getColorClass(percentage)}`;
        }

        if (label) {
            label.textContent = `${percentage.toFixed(1)}%`;
        }
    }

    getColorClass(percentage) {
        if (percentage >= 80) return 'mp-strong';
        if (percentage >= 50) return 'mp-medium';
        return 'mp-weak';
    }

    updateNextReview(isoTimestamp) {
        const reviewElement = this.container.querySelector('.mp-next-review');
        if (!reviewElement) return;

        const nextDate = new Date(isoTimestamp);
        const now = new Date();
        const diff = nextDate - now;

        if (diff < 0) {
            reviewElement.textContent = 'Due now!';
            return;
        }

        // Convert to human-readable format
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        let text = '';
        if (days > 0) {
            text = `in ${days} day${days > 1 ? 's' : ''}`;
        } else if (hours > 0) {
            text = `in ${hours} hour${hours > 1 ? 's' : ''}`;
        } else if (minutes > 0) {
            text = `in ${minutes} min`;
        } else {
            text = 'in < 1 min';
        }

        reviewElement.textContent = text;
    }

    show() {
        if (this.container) {
            this.container.style.display = 'block';
            this.isVisible = true;
        }
    }

    hide() {
        if (this.container) {
            this.container.style.display = 'none';
            this.isVisible = false;
        }
    }

    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
}

// Global instance
let memoryPowerWidget = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    memoryPowerWidget = new MemoryPowerWidget();
});

// Helper function to update widget from answer response
function updateMemoryPowerFromResponse(response) {
    if (memoryPowerWidget && response.memory_power) {
        memoryPowerWidget.update(response.memory_power);
    }
}
