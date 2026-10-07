/**
 * TRADENZA AUDIO ENGINE
 * High-performance synthesized UI sound effects to create a tactile, native-app feel.
 * Used for hovers, clicks, alerts, and trading feedback without loading external audio files.
 */
(function() {
    'use strict';

    let audioCtx = null;
    let isEnabled = true;

    function initAudio() {
        if (!audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            audioCtx = new AudioContext();
        }
        if (audioCtx.state === 'suspended') {
            audioCtx.resume();
        }
    }

    // Attempt to unlock audio context on first user interaction
    ['click', 'keydown', 'touchstart'].forEach(evt => {
        window.addEventListener(evt, initAudio, { once: true });
    });

    const playTone = (freq, type, duration, vol=0.1) => {
        if (!audioCtx || !isEnabled) return;
        
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        
        osc.type = type;
        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
        
        gain.gain.setValueAtTime(vol, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
        
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        
        osc.start();
        osc.stop(audioCtx.currentTime + duration);
    };

    window.TradenzaAudio = {
        hover: () => playTone(600, 'sine', 0.05, 0.02),
        click: () => playTone(800, 'triangle', 0.08, 0.05),
        win: () => {
            if(!audioCtx) return;
            playTone(440, 'sine', 0.1, 0.05);
            setTimeout(() => playTone(554, 'sine', 0.1, 0.05), 100);
            setTimeout(() => playTone(659, 'sine', 0.3, 0.05), 200);
        },
        loss: () => {
            if(!audioCtx) return;
            playTone(300, 'sawtooth', 0.2, 0.03);
            setTimeout(() => playTone(250, 'sawtooth', 0.3, 0.03), 150);
        },
        toggle: () => {
            isEnabled = !isEnabled;
            console.log("UI Sounds:", isEnabled);
        }
    };

    // Attach to DOM globally
    document.addEventListener('DOMContentLoaded', () => {
        // Attach hover sounds to interactive elements
        const hoverElements = document.querySelectorAll('a, button, .cmd-result-item, .trade-row-3d, .viz-tab');
        hoverElements.forEach(el => {
            el.addEventListener('mouseenter', () => TradenzaAudio.hover());
            el.addEventListener('mousedown', () => TradenzaAudio.click());
        });
    });

})();
