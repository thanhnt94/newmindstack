/**
 * SessionDriverClient
 * ====================
 * Frontend client for the unified Session Driver API.
 *
 * API endpoints consumed:
 *   POST /session/api/start           → Start a new driven session
 *   GET  /session/api/<id>/next       → Get next interaction
 *   POST /session/api/<id>/submit     → Submit an answer
 *
 * Usage:
 *   const client = new SessionDriverClient();
 *
 *   const { session_id } = await client.startSession(42, 'mcq', { num_choices: 4 });
 *   const interaction    = await client.getNextItem(session_id);
 *   const result         = await client.submitAnswer(session_id, {
 *       item_id: interaction.item_id,
 *       answer_index: 2,
 *       correct_index: interaction.data.correct_index,
 *   });
 */

window.SessionDriverClient = class SessionDriverClient {

    /**
     * @param {Object}  options
     * @param {string}  [options.baseUrl='/session/api']  API base path
     * @param {string}  [options.csrfToken]               CSRF token for POST requests
     */
    constructor({ baseUrl = '/session/api', csrfToken = null } = {}) {
        this.baseUrl   = baseUrl.replace(/\/+$/, '');   // strip trailing slash
        this.csrfToken = csrfToken;
    }

    // ── Public API ──────────────────────────────────────────────────

    /**
     * Start a new driven session.
     *
     * @param   {number}  containerId   ID of the LearningContainer
     * @param   {string}  mode          Learning mode ('mcq', 'flashcard', 'typing' …)
     * @param   {Object}  [settings={}] Mode-specific settings
     * @returns {Promise<Object>}       { session_id, total_items, learning_mode, item_queue_length }
     */
    async startSession(containerId, mode, settings = {}) {
        const data = await this._post('/start', {
            container_id:   containerId,
            learning_mode:  mode,
            settings,
        });
        console.log('[SessionDriver] Session started:', data.session_id,
                     `(${data.total_items} items, mode=${data.learning_mode})`);
        return data;
    }

    /**
     * Fetch the next interaction for a running session.
     *
     * @param   {number}  sessionId
     * @returns {Promise<Object>}   InteractionPayload or { finished: true, summary: {...} }
     */
    async getNextItem(sessionId) {
        const data = await this._get(`/${sessionId}/next`);

        if (data.finished) {
            console.log('[SessionDriver] Session finished:', data.summary);
        } else {
            console.log('[SessionDriver] Next item:',
                         data.item_id, `(type=${data.interaction_type})`);
        }
        return data;
    }

    /**
     * Submit an answer / rating for the current item.
     *
     * @param   {number}  sessionId
     * @param   {Object}  payload     Must include `item_id` plus mode-specific fields
     *                                MCQ:       { item_id, answer_index, correct_index }
     *                                Flashcard: { item_id, quality }   (1-4)
     * @returns {Promise<Object>}     SubmissionResult { is_correct, quality, score_change, feedback, srs_update }
     */
    async submitAnswer(sessionId, payload) {
        if (!payload || payload.item_id == null) {
            throw new Error('[SessionDriver] payload.item_id is required');
        }

        const data = await this._post(`/${sessionId}/submit`, payload);

        const icon = data.is_correct ? '✅' : '❌';
        console.log(`[SessionDriver] ${icon} item=${data.item_id}`,
                     `quality=${data.quality} score=${data.score_change}`);
        return data;
    }

    // ── Private helpers ─────────────────────────────────────────────

    /**
     * Build common headers for fetch requests.
     * @returns {Object}
     */
    _headers() {
        const h = { 'Content-Type': 'application/json' };
        if (this.csrfToken) {
            h['X-CSRFToken'] = this.csrfToken;
        }
        return h;
    }

    /**
     * GET request with error handling.
     * @param {string} path  Relative to baseUrl
     */
    async _get(path) {
        const url = `${this.baseUrl}${path}`;
        try {
            const res = await fetch(url, {
                method: 'GET',
                credentials: 'same-origin',
            });
            return await this._handleResponse(res);
        } catch (err) {
            console.error(`[SessionDriver] GET ${path} failed:`, err);
            throw err;
        }
    }

    /**
     * POST request with JSON body and error handling.
     * @param {string} path     Relative to baseUrl
     * @param {Object} body     JSON-serialisable payload
     */
    async _post(path, body) {
        const url = `${this.baseUrl}${path}`;
        try {
            const res = await fetch(url, {
                method:      'POST',
                credentials: 'same-origin',
                headers:     this._headers(),
                body:        JSON.stringify(body),
            });
            return await this._handleResponse(res);
        } catch (err) {
            console.error(`[SessionDriver] POST ${path} failed:`, err);
            throw err;
        }
    }

    /**
     * Parse response JSON and throw on non-2xx status.
     * @param {Response} res
     */
    async _handleResponse(res) {
        let data;
        try {
            data = await res.json();
        } catch {
            throw new Error(`[SessionDriver] Invalid JSON from server (status ${res.status})`);
        }

        if (!res.ok) {
            const msg = data?.error || `HTTP ${res.status}`;
            console.error(`[SessionDriver] API error:`, msg);
            throw new Error(msg);
        }
        return data;
    }
};
