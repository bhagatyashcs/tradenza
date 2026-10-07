/**
 * TRADENZA 3D PROFESSIONAL TRADING ENGINE
 * - Interactive Three.js Spatial Financial Cyber-Grid & Floating Market Topology
 * - Tactile 3D Card Tilt Physics with Dynamic Specular Glare
 * - Live Pulsing 3D Market Ticker Tape
 * - Keyboard Command Palette (Ctrl+K)
 */

(function () {
    'use strict';

    // =========================================================================
    // 1. THREE.JS 3D SPATIAL BACKGROUND ENGINE
    // =========================================================================

    let scene, camera, renderer, particles, gridLines, floatingPrisms = [];
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    let windowHalfX = window.innerWidth / 2;
    let windowHalfY = window.innerHeight / 2;
    let is3dEnabled = localStorage.getItem('tradenza_3d_fx') !== 'disabled';
    let animationFrameId = null;

    function init3DBackground() {
        const canvas = document.getElementById('webgl-trading-canvas');
        if (!canvas) return;

        if (typeof THREE === 'undefined') {
            console.warn('[Tradenza 3D] Three.js not loaded. Skipping WebGL scene.');
            return;
        }

        // Scene & Camera
        scene = new THREE.Scene();
        camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 2000);
        camera.position.z = 600;
        camera.position.y = 150;
        camera.lookAt(0, 0, 0);

        // WebGL Renderer
        renderer = new THREE.WebGLRenderer({
            canvas: canvas,
            alpha: true,
            antialias: true,
            powerPreference: 'high-performance'
        });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

        // 1. Undulating Market Grid Topology (Orderbook Depth Waves)
        const gridGeometry = new THREE.PlaneGeometry(1600, 1600, 32, 32);
        gridGeometry.rotateX(-Math.PI / 2);

        // Add subtle wave displacement to vertices
        const pos = gridGeometry.attributes.position;
        for (let i = 0; i < pos.count; i++) {
            const vx = pos.getX(i);
            const vz = pos.getZ(i);
            const dist = Math.sqrt(vx * vx + vz * vz);
            const vy = Math.sin(vx * 0.008) * 35 + Math.cos(vz * 0.008) * 35 - 120;
            pos.setY(i, vy);
        }
        gridGeometry.computeVertexNormals();

        const gridMaterial = new THREE.MeshBasicMaterial({
            color: 0x00d2ff,
            wireframe: true,
            transparent: true,
            opacity: 0.12
        });
        gridLines = new THREE.Mesh(gridGeometry, gridMaterial);
        gridLines.position.y = -180;
        scene.add(gridLines);

        // 2. Floating Financial Constellation Particles
        const particleCount = 280;
        const particleGeometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        const colors = new Float32Array(particleCount * 3);

        const colorPalette = [
            new THREE.Color(0x00d2ff), // Cyan
            new THREE.Color(0x00f59b), // Emerald
            new THREE.Color(0xa855f7), // Purple
            new THREE.Color(0x38bdf8)  // Sky
        ];

        for (let i = 0; i < particleCount; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 1400;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 700 + 40;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 1000;

            const col = colorPalette[Math.floor(Math.random() * colorPalette.length)];
            colors[i * 3] = col.r;
            colors[i * 3 + 1] = col.g;
            colors[i * 3 + 2] = col.b;
        }

        particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        particleGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        // Canvas texture for smooth glowing dots
        const particleCanvas = document.createElement('canvas');
        particleCanvas.width = 16;
        particleCanvas.height = 16;
        const ctx = particleCanvas.getContext('2d');
        const grad = ctx.createRadialGradient(8, 8, 0, 8, 8, 8);
        grad.addColorStop(0, 'rgba(255,255,255,1)');
        grad.addColorStop(0.4, 'rgba(0,210,255,0.8)');
        grad.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 16, 16);
        const particleTexture = new THREE.CanvasTexture(particleCanvas);

        const particleMaterial = new THREE.PointsMaterial({
            size: 6,
            map: particleTexture,
            vertexColors: true,
            transparent: true,
            opacity: 0.7,
            blending: THREE.AdditiveBlending,
            depthWrite: false
        });

        particles = new THREE.Points(particleGeometry, particleMaterial);
        scene.add(particles);

        // 3. Floating 3D Candlestick & Data Prisms
        const prismMaterials = [
            new THREE.MeshBasicMaterial({ color: 0x00f59b, wireframe: true, transparent: true, opacity: 0.28 }),
            new THREE.MeshBasicMaterial({ color: 0xff3366, wireframe: true, transparent: true, opacity: 0.25 }),
            new THREE.MeshBasicMaterial({ color: 0x00d2ff, wireframe: true, transparent: true, opacity: 0.22 })
        ];

        for (let i = 0; i < 18; i++) {
            const h = 25 + Math.random() * 65;
            const geom = new THREE.BoxGeometry(10 + Math.random() * 10, h, 10 + Math.random() * 10);
            const mat = prismMaterials[i % prismMaterials.length];
            const mesh = new THREE.Mesh(geom, mat);
            
            mesh.position.set(
                (Math.random() - 0.5) * 1200,
                (Math.random() - 0.5) * 450,
                (Math.random() - 0.5) * 800
            );
            mesh.rotation.x = Math.random() * Math.PI;
            mesh.rotation.y = Math.random() * Math.PI;
            
            mesh.userData = {
                rotSpeedX: (Math.random() - 0.5) * 0.008,
                rotSpeedY: (Math.random() - 0.5) * 0.008,
                driftSpeedY: (Math.random() - 0.5) * 0.2
            };

            floatingPrisms.push(mesh);
            scene.add(mesh);
        }

        // Mouse Parallax Listeners
        window.addEventListener('mousemove', onMouseMove, { passive: true });
        window.addEventListener('resize', onWindowResize, { passive: true });

        if (is3dEnabled) {
            animate3D();
        } else {
            document.body.classList.add('canvas-disabled');
        }
    }

    function onMouseMove(event) {
        mouseX = (event.clientX - windowHalfX) * 0.15;
        mouseY = (event.clientY - windowHalfY) * 0.15;
    }

    function onWindowResize() {
        if (!renderer || !camera) return;
        windowHalfX = window.innerWidth / 2;
        windowHalfY = window.innerHeight / 2;
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }

    function animate3D() {
        if (!is3dEnabled) return;
        animationFrameId = requestAnimationFrame(animate3D);

        // Smooth Camera Easing (Parallax)
        targetX += (mouseX - targetX) * 0.04;
        targetY += (mouseY - targetY) * 0.04;

        camera.position.x = targetX * 0.8;
        camera.position.y = 150 - (targetY * 0.6);
        camera.lookAt(0, 0, 0);

        // Slowly rotate grid & pulse
        if (gridLines) {
            gridLines.rotation.y += 0.0006;
        }

        // Slowly rotate constellation particles
        if (particles) {
            particles.rotation.y += 0.0004;
            particles.rotation.x += 0.0002;
        }

        // Animate floating prisms
        for (let i = 0; i < floatingPrisms.length; i++) {
            const p = floatingPrisms[i];
            p.rotation.x += p.userData.rotSpeedX;
            p.rotation.y += p.userData.rotSpeedY;
            p.position.y += p.userData.driftSpeedY;

            // Loop back when drifting too high/low
            if (p.position.y > 350) p.position.y = -350;
            if (p.position.y < -350) p.position.y = 350;
        }

        renderer.render(scene, camera);
    }

    // Toggle 3D FX
    window.toggleTradenza3DFX = function () {
        is3dEnabled = !is3dEnabled;
        localStorage.setItem('tradenza_3d_fx', is3dEnabled ? 'enabled' : 'disabled');
        
        if (is3dEnabled) {
            document.body.classList.remove('canvas-disabled');
            if (!animationFrameId) animate3D();
        } else {
            document.body.classList.add('canvas-disabled');
            if (animationFrameId) {
                cancelAnimationFrame(animationFrameId);
                animationFrameId = null;
            }
        }

        // Update button appearance if present
        const btn = document.getElementById('fxToggleBtn');
        if (btn) {
            btn.style.opacity = is3dEnabled ? '1' : '0.4';
            btn.title = is3dEnabled ? '3D Atmosphere: Active' : '3D Atmosphere: Paused';
        }
    };


    // =========================================================================
    // 2. TACTILE 3D CARD TILT & SPECULAR GLARE ENGINE
    // =========================================================================

    function initCardTiltPhysics() {
        const selector = '.card-3d, .dashboard-card, .quality-card, .aura-card, .dash-hero, .trade-summary-card, .scanner-box, .portfolio-card';
        const cards = document.querySelectorAll(selector);

        cards.forEach(card => {
            // Create glare element if not present
            if (!card.querySelector('.card-3d-glare')) {
                const glare = document.createElement('div');
                glare.className = 'card-3d-glare';
                card.appendChild(glare);
            }

            card.addEventListener('mousemove', e => handleCardTilt(e, card), { passive: true });
            card.addEventListener('mouseleave', () => resetCardTilt(card), { passive: true });
        });
    }

    function handleCardTilt(event, card) {
        const rect = card.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;

        // Normalized mouse coordinate from -1 to 1
        const mouseX = (event.clientX - rect.left) / width;
        const mouseY = (event.clientY - rect.top) / height;

        const rotateX = (mouseY - 0.5) * -12; // Max 6 deg tilt
        const rotateY = (mouseX - 0.5) * 14;

        card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateZ(8px) scale3d(1.015, 1.015, 1.015)`;

        // Update Specular Glare Sheen
        const glare = card.querySelector('.card-3d-glare');
        if (glare) {
            glare.style.opacity = '0.35';
            glare.style.background = `radial-gradient(circle at ${(mouseX * 100).toFixed(1)}% ${(mouseY * 100).toFixed(1)}%, rgba(255, 255, 255, 0.28) 0%, rgba(255, 255, 255, 0) 65%)`;
        }
    }

    function resetCardTilt(card) {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0) scale3d(1, 1, 1)';
        const glare = card.querySelector('.card-3d-glare');
        if (glare) {
            glare.style.opacity = '0';
        }
    }


    // =========================================================================
    // 3. LIVE 3D MARKET TICKER MICRO-SIMULATOR
    // =========================================================================

    function initMarketTickerPulse() {
        const tickerTrack = document.getElementById('tradingTickerTrack');
        if (!tickerTrack) return;

        // Random price ticks every 3.5s to create high-frequency adrenaline
        setInterval(() => {
            const items = tickerTrack.querySelectorAll('.ticker-item');
            if (!items.length) return;

            // Pick 1-2 random tickers to update
            const randIdx = Math.floor(Math.random() * items.length);
            const item = items[randIdx];
            const priceEl = item.querySelector('.ticker-price');
            const changeEl = item.querySelector('.ticker-change');
            if (!priceEl) return;

            let currentPrice = parseFloat(priceEl.innerText.replace(/[^0-9.]/g, ''));
            if (isNaN(currentPrice)) return;

            const isUp = Math.random() > 0.46;
            const deltaPercent = (Math.random() * 0.08 + 0.01) * (isUp ? 1 : -1);
            const newPrice = currentPrice * (1 + (deltaPercent / 100));

            // Format based on magnitude
            let formattedPrice = '';
            if (newPrice > 1000) {
                formattedPrice = '$' + newPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            } else if (newPrice > 10) {
                formattedPrice = '$' + newPrice.toFixed(2);
            } else {
                formattedPrice = '$' + newPrice.toFixed(4);
            }

            priceEl.innerText = formattedPrice;

            // Flash effect
            const flashClass = isUp ? 'tick-flash-green' : 'tick-flash-red';
            priceEl.classList.add(flashClass);
            setTimeout(() => {
                priceEl.classList.remove(flashClass);
            }, 650);

            if (changeEl) {
                const sign = isUp ? '+' : '';
                changeEl.innerText = `${sign}${(Math.abs(deltaPercent) * 10).toFixed(2)}%`;
                if (isUp) {
                    changeEl.className = 'ticker-change ticker-up';
                } else {
                    changeEl.className = 'ticker-change ticker-down';
                }
            }
        }, 3200);
    }


    // =========================================================================
    // 4. 3D QUICK COMMAND PALETTE (CTRL+K)
    // =========================================================================

    function initCommandPalette() {
        const backdrop = document.getElementById('cmdPaletteBackdrop');
        const input = document.getElementById('cmdPaletteInput');
        const list = document.getElementById('cmdResultsList');
        if (!backdrop || !input) return;

        function openPalette() {
            backdrop.classList.add('active');
            input.value = '';
            input.focus();
            filterItems('');
        }

        function closePalette() {
            backdrop.classList.remove('active');
        }

        // Open via shortcut or search button
        window.addEventListener('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
                e.preventDefault();
                if (backdrop.classList.contains('active')) {
                    closePalette();
                } else {
                    openPalette();
                }
            } else if (e.key === 'Escape' && backdrop.classList.contains('active')) {
                closePalette();
            }
        });

        const openBtn = document.getElementById('topbarSearchBtn');
        if (openBtn) {
            openBtn.addEventListener('click', openPalette);
        }

        backdrop.addEventListener('click', e => {
            if (e.target === backdrop) closePalette();
        });

        // Filter items
        input.addEventListener('input', () => {
            filterItems(input.value.toLowerCase().trim());
        });

        function filterItems(query) {
            if (!list) return;
            const items = list.querySelectorAll('.cmd-result-item');
            items.forEach(item => {
                const text = item.innerText.toLowerCase();
                if (!query || text.includes(query)) {
                    item.style.display = 'flex';
                } else {
                    item.style.display = 'none';
                }
            });
        }
    }


    // =========================================================================
    // 5. MOBILE DRAWER NAVIGATION
    // =========================================================================

    function initMobileNavigation() {
        const toggleBtn = document.getElementById('mobileMenuBtn');
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        if (!toggleBtn || !sidebar || !overlay) return;

        function toggle() {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        }

        toggleBtn.addEventListener('click', toggle);
        overlay.addEventListener('click', toggle);
    }


    // =========================================================================
    // INITIALIZATION ON DOM READY
    // =========================================================================

    document.addEventListener('DOMContentLoaded', () => {
        init3DBackground();
        initCardTiltPhysics();
        initMarketTickerPulse();
        initCommandPalette();
        initMobileNavigation();

        // Refresh icons if lucide is available
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    });

})();
