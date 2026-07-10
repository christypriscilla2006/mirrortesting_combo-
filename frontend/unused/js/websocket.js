/* websocket.js — Phase 4: Backend Communication */

const WS_URL = `ws://${window.location.host}/ws/stream`;
let socket = null;
let pingInterval = null;

function connect() {
    console.log(`[WS] Connecting to ${WS_URL}...`);
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log('[WS] Connected to backend');
        const wsDot = document.getElementById('ws-dot');
        if (wsDot) wsDot.classList.add('active');
        
        // Start pinging to keep connection alive
        pingInterval = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send('ping');
            }
        }, 20000);
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'pong') return;

        if (data.type === 'state_update') {
            console.log('[WS] State update:', data);
            window.dispatchEvent(new CustomEvent('mg:state_update', { detail: data }));
        } else if (data.type === 'telemetry') {
            window.dispatchEvent(new CustomEvent('mg:telemetry', { detail: data }));
        }
    };

    socket.onclose = () => {
        console.warn('[WS] Disconnected. Reconnecting in 3s...');
        const wsDot = document.getElementById('ws-dot');
        if (wsDot) wsDot.classList.remove('active');
        if (pingInterval) clearInterval(pingInterval);
        setTimeout(connect, 3000);
    };

    socket.onerror = (err) => {
        console.error('[WS] Error:', err);
        socket.close(); // Force close to trigger reconnect
    };
}

// Start connection
connect();
