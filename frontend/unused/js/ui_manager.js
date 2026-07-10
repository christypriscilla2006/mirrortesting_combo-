/* ui_manager.js — Phase 5: 5-Page UI & Telemetry Management */

const API_URL = `http://${window.location.host}/api/data`;

let currentData = null;
let currentMode = 'boot'; 
let currentPage = 0;
let hideHudTimeout = null;
let particleTimeout = null;

// DOM Elements
const elBody = document.body;
const elIntro = document.getElementById('intro-container');
const elGestureHud = document.getElementById('gesture-hud');
const elGestureIcon = document.getElementById('gesture-icon');
const elGestureLabel = document.getElementById('gesture-label');
const elApiDot = document.getElementById('api-dot');

const GESTURE_ICONS = {
    'open_palm': '✋',
    'closed_fist': '✊',
    'swipe_left': '👈',
    'swipe_right': '👉',
    'thumbs_up': '👍'
};

const GESTURE_LABELS = {
    'open_palm': 'HOME',
    'closed_fist': 'SLEEP',
    'swipe_left': 'PAGE R',
    'swipe_right': 'PAGE L',
    'thumbs_up': 'NEXT'
};

// 1. Fetch initial data
async function fetchData() {
    try {
        const res = await fetch(API_URL);
        if (!res.ok) throw new Error('API offline');
        currentData = await res.json();
        populateUI();
        if (elApiDot) elApiDot.classList.add('active');
    } catch (err) {
        console.error('[API] Fetch failed:', err);
        if (elApiDot) elApiDot.classList.remove('active');
        setTimeout(fetchData, 5000); // Retry
    }
}

// 2. Populate UI with data
function populateUI() {
    if (!currentData) return;

    // --- Page 1: Briefing ---
    document.getElementById('task-title').textContent = currentData.task.title;
    document.getElementById('task-priority').textContent = currentData.task.priority;
    document.getElementById('task-due').textContent = 'DUE: ' + currentData.task.due;
    
    const subtasksEl = document.getElementById('task-subtasks');
    subtasksEl.innerHTML = '';
    let doneCount = 0;
    currentData.task.subtasks.forEach(st => {
        if (st.done) doneCount++;
        subtasksEl.innerHTML += `
            <li class="subtask-item ${st.done ? 'done' : ''}">
                <div class="subtask-check">${st.done ? '✓' : ''}</div>
                <span>${st.label}</span>
            </li>
        `;
    });
    
    const pct = Math.round((doneCount / currentData.task.subtasks.length) * 100);
    document.getElementById('task-progress-pct').textContent = `${pct}%`;
    document.getElementById('task-progress-fill').style.width = `${pct}%`;

    document.getElementById('weather-condition').textContent = currentData.weather.condition.toUpperCase();
    document.getElementById('weather-temp').textContent = `${currentData.weather.temp_c}°`;
    document.getElementById('weather-humidity').textContent = `${currentData.weather.humidity_pct}%`;
    document.getElementById('weather-wind').textContent = `${currentData.weather.wind_kph} KPH`;
    document.getElementById('weather-location').textContent = currentData.weather.location.toUpperCase();

    const forecastEl = document.getElementById('weather-forecast');
    forecastEl.innerHTML = '';
    currentData.weather.forecast.forEach(f => {
        forecastEl.innerHTML += `
            <div class="forecast-card">
                <span class="forecast-day">${f.day}</span>
                <span class="forecast-icon">${f.icon}</span>
                <span class="forecast-hi">${f.high}°</span>
                <span class="forecast-lo">${f.low}°</span>
            </div>
        `;
    });

    // --- Page 2: Commute ---
    if (currentData.traffic) {
        document.getElementById('traffic-route').textContent = currentData.traffic.location.toUpperCase();
        document.getElementById('traffic-eta').textContent = `${currentData.traffic.eta_mins} MINS`;
        document.getElementById('traffic-status').textContent = `STATUS: ${currentData.traffic.status.toUpperCase()}`;
        document.getElementById('traffic-incidents').textContent = currentData.traffic.incidents;
        document.getElementById('traffic-trend').textContent = currentData.traffic.trend.toUpperCase();
    }

    // --- Page 3: Emails ---
    if (currentData.emails) {
        const emailEl = document.getElementById('email-list');
        emailEl.innerHTML = '';
        currentData.emails.forEach(email => {
            emailEl.innerHTML += `
                <li style="border: 1px solid var(--cyan-border); padding: 10px; border-radius: 4px; background: var(--cyan-dim);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                        <span style="font-weight: bold; color: var(--cyan);">${email.sender.toUpperCase()}</span>
                        <span style="font-size: 0.7rem; color: rgba(0,243,255,0.6);">${email.time}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #fff;">${email.subject}</div>
                </li>
            `;
        });
    }

    // --- Header / Footer System Info ---
    document.getElementById('hostname').textContent = currentData.system.hostname.toUpperCase();
    document.getElementById('uptime').textContent = `UP ${currentData.system.uptime_hrs}H`;
}

// 3. Handle State Updates from WS
window.addEventListener('mg:state_update', (e) => {
    const state = e.detail;
    console.log('[UI] Transitioning to state:', state);
    
    // Show gesture HUD
    if (state.gesture && state.gesture !== 'none') {
        showGestureHUD(state.gesture);
    }

    // Manage base classes and page classes
    let classes = [];
    if (state.mode === 'sleep') {
        classes.push('state-sleep');
        if (window.MG_Particles) window.MG_Particles.pause();
    } else {
        classes.push('state-wake');
        classes.push(`page-${state.page}`);
        
        // Start particles dynamically on interaction
        if (window.MG_Particles) window.MG_Particles.start();
        scheduleParticlePause();
    }

    elBody.className = classes.join(' ');
    currentMode = state.mode;
    currentPage = state.page;
});

// Listen for live telemetry
window.addEventListener('mg:telemetry', (e) => {
    const data = e.detail;
    // Only update if we're actually on the telemetry page to save DOM updates
    if (currentPage === 4 && currentMode === 'wake') {
        document.getElementById('telemetry-cpu-val').textContent = `${data.cpu.toFixed(1)}%`;
        document.getElementById('telemetry-cpu-bar').style.width = `${data.cpu}%`;
        
        document.getElementById('telemetry-ram-val').textContent = `${data.ram.toFixed(1)}%`;
        document.getElementById('telemetry-ram-bar').style.width = `${data.ram}%`;
    }
});

function scheduleParticlePause() {
    if (particleTimeout) clearTimeout(particleTimeout);
    particleTimeout = setTimeout(() => {
        if (window.MG_Particles && currentMode === 'wake') {
            window.MG_Particles.pause();
        }
    }, 4000); 
}

function showGestureHUD(gesture) {
    if (!GESTURE_ICONS[gesture]) return;
    
    elGestureIcon.textContent = GESTURE_ICONS[gesture];
    elGestureLabel.textContent = GESTURE_LABELS[gesture];
    elGestureHud.classList.add('visible');
    
    elGestureIcon.style.animation = 'none';
    void elGestureIcon.offsetWidth; 
    elGestureIcon.style.animation = 'gestureIconPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards';

    if (hideHudTimeout) clearTimeout(hideHudTimeout);
    hideHudTimeout = setTimeout(() => {
        elGestureHud.classList.remove('visible');
    }, 1500);
}

// 5. FPS Counter (Native JS)
let frameCount = 0;
let lastFpsTime = performance.now();
function fpsLoop() {
    frameCount++;
    const now = performance.now();
    if (now - lastFpsTime >= 1000) {
        if (currentPage === 4 && currentMode === 'wake') {
            const fpsEl = document.getElementById('telemetry-fps');
            if (fpsEl) fpsEl.textContent = `${frameCount} FPS`;
        }
        frameCount = 0;
        lastFpsTime = now;
    }
    requestAnimationFrame(fpsLoop);
}
requestAnimationFrame(fpsLoop);

// Boot
function startBootSequence() {
    setTimeout(() => {
        elIntro.style.opacity = '0';
        setTimeout(() => {
            elIntro.style.display = 'none';
            if (currentMode === 'boot') {
                elBody.className = 'state-wake page-0';
            }
        }, 1500);
    }, 4000);
}

startBootSequence();
fetchData();
setInterval(fetchData, 300000);

// 6. Keyboard Fallbacks for Testing
window.addEventListener('keydown', (e) => {
    let gesture = null;
    switch (e.key) {
        case 'ArrowRight': gesture = 'swipe_left'; break;
        case 'ArrowLeft': gesture = 'swipe_right'; break;
        case 'w': case 'W': gesture = 'open_palm'; break;
        case 's': case 'S': gesture = 'closed_fist'; break;
    }
    
    if (gesture) {
        console.log(`[UI] Keyboard fallback triggered: ${gesture}`);
        // Send to backend via HTTP POST
        fetch(`http://${window.location.host}/api/gesture/${gesture}`, { method: 'POST' })
            .catch(err => console.error('[API] Gesture inject failed:', err));
    }
});
