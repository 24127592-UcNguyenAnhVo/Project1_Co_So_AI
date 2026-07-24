import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const TILE_HEIGHT = 0.18;
const TILE_TOP = TILE_HEIGHT / 2;
const CUBE_SIZE = 1.0;
const REPLAY_DELAY_MS = 260;
const TRACE_DELAY_MS = 55;

const COLORS = {
    floor: 0xd6d6d6,
    floorSide: 0x8d8d8d,
    goal: 0xd7a92f,
    fragile: 0xd47c35,
    soft: 0x65b9d8,
    heavy: 0xb95d5d,
    split: 0x9b78b8,
    bridgeOpen: 0x78a978,
    bridgeClosed: 0x666666,
    block: 0x000080,
    activeCube: 0xb8754d,
    inactiveCube: 0x684531,
};

const dom = {
    sceneContainer: document.querySelector('#scene-container'),
    levelSelect: document.querySelector('#level-select'),
    newGame: document.querySelector('#new-game-btn'),
    restart: document.querySelector('#restart-btn'),
    camera: document.querySelector('#camera-btn'),
    visualize: document.querySelector('#visualize-toggle'),
    replay: document.querySelector('#replay-btn'),
    solverButtons: [...document.querySelectorAll('.solver-btn')],
    statusText: document.querySelector('#status-text'),
    statusBar: document.querySelector('#status'),
    loading: document.querySelector('#loading-overlay'),
    loadingText: document.querySelector('#loading-text'),
    algorithm: document.querySelector('#algorithm-badge'),
    time: document.querySelector('#metric-time'),
    memory: document.querySelector('#metric-memory'),
    expanded: document.querySelector('#metric-expanded'),
    frontier: document.querySelector('#metric-frontier'),
    length: document.querySelector('#metric-length'),
    cost: document.querySelector('#metric-cost'),
    path: document.querySelector('#solution-path'),
};

let currentSnapshot = null;
let currentDisplayState = null;
let lastSolution = [];
let busy = false;
let replaying = false;
let scene;
let camera;
let renderer;
let controls;
let boardGroup;
let blockGroup;
let lightsGroup;

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {}),
        },
        ...options,
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || `Request failed: ${response.status}`);
    }

    return data;
}

function setStatus(message, type = 'normal') {
    dom.statusText.textContent = message;
    dom.statusBar.dataset.type = type;

    const dot = dom.statusBar.querySelector('.status-dot');
    const colors = {
        normal: '#55e6a5',
        warning: '#ffca5c',
        error: '#ff607a',
        search: '#4be1ff',
    };
    dot.style.background = colors[type] || colors.normal;
    dot.style.boxShadow = `0 0 12px ${colors[type] || colors.normal}`;
}

function setBusy(value, text = 'Searching...') {
    busy = value;
    dom.loading.classList.toggle('hidden', !value);
    dom.loadingText.textContent = text;
    dom.solverButtons.forEach(button => button.disabled = value);
    dom.newGame.disabled = value;
    dom.restart.disabled = value;
    dom.levelSelect.disabled = value;
}

function clearMetrics() {
    dom.algorithm.textContent = '—';
    dom.time.textContent = '—';
    dom.memory.textContent = '—';
    dom.expanded.textContent = '—';
    dom.frontier.textContent = '—';
    dom.length.textContent = '—';
    dom.cost.textContent = '—';
    dom.path.textContent = 'Run a solver to generate a solution.';
    dom.replay.disabled = true;
    lastSolution = [];
}

function updateMetrics(result) {
    dom.algorithm.textContent = result.algorithm;
    dom.time.textContent = `${result.time_sec.toFixed(6)} s`;
    dom.memory.textContent = `${(result.peak_memory_bytes / 1024).toFixed(2)} KB`;
    dom.expanded.textContent = result.expanded_nodes;
    dom.frontier.textContent = 'Finished';
    dom.length.textContent = result.solution_length;
    dom.cost.textContent = result.total_cost == null ? '—' : Number(result.total_cost).toFixed(2);

    lastSolution = result.path || [];
    dom.path.innerHTML = '';

    if (!result.found || lastSolution.length === 0) {
        dom.path.textContent = result.found ? 'Already at the goal.' : 'No solution found.';
        dom.replay.disabled = true;
        return;
    }

    for (const action of lastSolution) {
        const token = document.createElement('span');
        token.className = 'move-token';
        token.textContent = action;
        dom.path.appendChild(token);
    }

    dom.replay.disabled = false;
}

function initializeThree() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xc94718);
    scene.fog = new THREE.FogExp2(0xc94718, 0.018);

    camera = new THREE.PerspectiveCamera(
        45,
        dom.sceneContainer.clientWidth / dom.sceneContainer.clientHeight,
        0.1,
        200,
    );

    renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(dom.sceneContainer.clientWidth, dom.sceneContainer.clientHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    dom.sceneContainer.appendChild(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 5;
    controls.maxDistance = 28;
    controls.maxPolarAngle = Math.PI * 0.47;
    controls.target.set(0, 0, 0);

    boardGroup = new THREE.Group();
    blockGroup = new THREE.Group();
    lightsGroup = new THREE.Group();

    scene.add(boardGroup);
    scene.add(blockGroup);
    scene.add(lightsGroup);

    const hemisphere = new THREE.HemisphereLight(0xbfe6ff, 0x1b2130, 2.2);
    lightsGroup.add(hemisphere);

    const keyLight = new THREE.DirectionalLight(0xffffff, 3.2);
    keyLight.position.set(7, 12, 6);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.set(2048, 2048);
    keyLight.shadow.camera.near = 0.5;
    keyLight.shadow.camera.far = 40;
    keyLight.shadow.camera.left = -14;
    keyLight.shadow.camera.right = 14;
    keyLight.shadow.camera.top = 14;
    keyLight.shadow.camera.bottom = -14;
    lightsGroup.add(keyLight);

    const rim = new THREE.DirectionalLight(0x627dff, 1.25);
    rim.position.set(-8, 6, -7);
    lightsGroup.add(rim);

    window.addEventListener('resize', resizeRenderer);
    animateScene();
}

function resizeRenderer() {
    if (!renderer || !camera) return;
    const width = dom.sceneContainer.clientWidth;
    const height = dom.sceneContainer.clientHeight;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
}

function animateScene() {
    requestAnimationFrame(animateScene);
    controls.update();
    renderer.render(scene, camera);
}

function resetCamera(board = currentSnapshot?.board) {
    if (!board) return;
    const span = Math.max(board.rows, board.cols);
    camera.position.set(span * 0.85, span * 1.05 + 3, span * 1.15);
    controls.target.set(0, 0.25, 0);
    controls.update();
}

function disposeObject(object) {
    object.traverse(child => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
            if (Array.isArray(child.material)) {
                child.material.forEach(material => material.dispose());
            } else {
                child.material.dispose();
            }
        }
    });
}

function clearGroup(group) {
    while (group.children.length > 0) {
        const child = group.children.pop();
        disposeObject(child);
    }
}

function cellToWorld(row, col, board) {
    return {
        x: col - (board.cols - 1) / 2,
        z: row - (board.rows - 1) / 2,
    };
}

function createTileMaterial(color, roughness = 0.72, metalness = 0.04) {
    return new THREE.MeshStandardMaterial({
        color,
        roughness,
        metalness,
    });
}

function createTileMesh(color, y = 0, opacity = 1) {
    const geometry = new THREE.BoxGeometry(0.98, TILE_HEIGHT, 0.98);
    const material = createTileMaterial(color);
    material.transparent = opacity < 1;
    material.opacity = opacity;

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.y = y;
    mesh.receiveShadow = true;
    mesh.castShadow = true;

    const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x24384d, transparent: true, opacity: 0.5 }),
    );
    mesh.add(edges);
    return mesh;
}

function addGoalMarker(group) {
    const ring = new THREE.Mesh(
        new THREE.TorusGeometry(0.24, 0.055, 12, 32),
        new THREE.MeshStandardMaterial({ color: 0x111820, roughness: 0.4 }),
    );
    ring.rotation.x = Math.PI / 2;
    ring.position.y = TILE_TOP + 0.018;
    group.add(ring);

    const hole = new THREE.Mesh(
        new THREE.CircleGeometry(0.18, 32),
        new THREE.MeshBasicMaterial({ color: 0x05080c }),
    );
    hole.rotation.x = -Math.PI / 2;
    hole.position.y = TILE_TOP + 0.02;
    group.add(hole);
}

function addSoftMarker(group) {
    const marker = new THREE.Mesh(
        new THREE.CylinderGeometry(0.22, 0.22, 0.055, 32),
        new THREE.MeshStandardMaterial({ color: COLORS.soft, emissive: 0x123b4a, emissiveIntensity: 0.45 }),
    );
    marker.position.y = TILE_TOP + 0.045;
    group.add(marker);
}

function addHeavyMarker(group) {
    for (const angle of [Math.PI / 4, -Math.PI / 4]) {
        const bar = new THREE.Mesh(
            new THREE.BoxGeometry(0.58, 0.055, 0.10),
            new THREE.MeshStandardMaterial({ color: COLORS.heavy, emissive: 0x4a1020, emissiveIntensity: 0.35 }),
        );
        bar.rotation.y = angle;
        bar.position.y = TILE_TOP + 0.045;
        group.add(bar);
    }
}

function addSplitMarker(group) {
    const material = new THREE.MeshStandardMaterial({
        color: COLORS.split,
        emissive: 0x28154a,
        emissiveIntensity: 0.55,
    });

    for (const direction of [-1, 1]) {
        const arc = new THREE.Mesh(
            new THREE.TorusGeometry(0.25, 0.055, 10, 20, Math.PI),
            material,
        );
        arc.rotation.x = Math.PI / 2;
        arc.rotation.z = direction === -1 ? Math.PI / 2 : -Math.PI / 2;
        arc.position.x = direction * 0.14;
        arc.position.y = TILE_TOP + 0.04;
        group.add(arc);
    }
}

function addFragileCracks(group) {
    const crackMaterial = new THREE.LineBasicMaterial({ color: 0x6f3218 });
    const pointsList = [
        [[-0.28, 0], [-0.04, 0.18], [0.05, -0.05], [0.26, 0.16]],
        [[-0.12, -0.30], [0.02, -0.08], [0.18, -0.28]],
    ];

    for (const points of pointsList) {
        const geometry = new THREE.BufferGeometry().setFromPoints(
            points.map(([x, z]) => new THREE.Vector3(x, TILE_TOP + 0.012, z)),
        );
        group.add(new THREE.Line(geometry, crackMaterial));
    }
}

function buildBoard(snapshot) {
    clearGroup(boardGroup);

    const board = snapshot.board;
    const bridgeStates = snapshot.state?.bridge_states || {};

    const ground = new THREE.Mesh(
        new THREE.PlaneGeometry(Math.max(board.cols + 14, 24), Math.max(board.rows + 14, 24)),
        new THREE.MeshStandardMaterial({ color: 0x4d1710, roughness: 1 }),
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.y = -0.22;
    ground.receiveShadow = true;
    boardGroup.add(ground);

    for (let row = 0; row < board.rows; row += 1) {
        for (let col = 0; col < board.cols; col += 1) {
            const tile = board.grid[row][col];
            if (tile === '0') continue;

            const cellKey = `${row},${col}`;
            const bridgeId = board.bridge_cells[cellKey];
            const isGoal = row === board.goal_pos[0] && col === board.goal_pos[1];

            let color = COLORS.floor;
            let tileY = 0;
            let opacity = 1;

            if (tile === 'F') color = COLORS.fragile;
            if (tile === 'O') color = COLORS.soft;
            if (tile === 'X') color = COLORS.heavy;
            if (tile === 'T') color = COLORS.split;
            if (isGoal) color = COLORS.goal;

            if (tile === 'B') {
                const isOpen = Boolean(bridgeStates[bridgeId]);
                color = isOpen ? COLORS.bridgeOpen : COLORS.bridgeClosed;
                tileY = isOpen ? 0 : -0.18;
                opacity = isOpen ? 1 : 0.42;
            }

            const tileGroup = new THREE.Group();
            const world = cellToWorld(row, col, board);
            tileGroup.position.set(world.x, 0, world.z);

            const tileMesh = createTileMesh(color, tileY, opacity);
            tileGroup.add(tileMesh);

            if (isGoal) addGoalMarker(tileGroup);
            if (tile === 'O') addSoftMarker(tileGroup);
            if (tile === 'X') addHeavyMarker(tileGroup);
            if (tile === 'T') addSplitMarker(tileGroup);
            if (tile === 'F') addFragileCracks(tileGroup);

            boardGroup.add(tileGroup);
        }
    }
}

function blockDescriptorsFromState(state, board) {
    if (!state) return [];

    if (state.is_split) {
        const cells = [
            [state.r, state.c],
            [state.cube2_r, state.cube2_c],
        ];

        return cells.map(([row, col], index) => {
            const world = cellToWorld(row, col, board);
            return {
                x: world.x,
                y: TILE_TOP + CUBE_SIZE / 2 + 0.01,
                z: world.z,
                width: CUBE_SIZE,
                height: CUBE_SIZE,
                depth: CUBE_SIZE,
                split: true,
                active: state.active_cube === index + 1,
            };
        });
    }

    if (state.orient === 'STANDING') {
        const world = cellToWorld(state.r, state.c, board);
        return [{
            x: world.x,
            y: TILE_TOP + CUBE_SIZE + 0.01,
            z: world.z,
            width: CUBE_SIZE,
            height: CUBE_SIZE * 2,
            depth: CUBE_SIZE,
            split: false,
            active: false,
        }];
    }

    const [[r1, c1], [r2, c2]] = state.positions;
    const w1 = cellToWorld(r1, c1, board);
    const w2 = cellToWorld(r2, c2, board);

    return [{
        x: (w1.x + w2.x) / 2,
        y: TILE_TOP + CUBE_SIZE / 2 + 0.01,
        z: (w1.z + w2.z) / 2,
        width: c1 !== c2 ? 2.0 : CUBE_SIZE,
        height: CUBE_SIZE,
        depth: r1 !== r2 ? 2.0 : CUBE_SIZE,
        split: false,
        active: false,
    }];
}

function createBlockMesh(descriptor) {
    const color = descriptor.split
        ? (descriptor.active ? COLORS.activeCube : COLORS.inactiveCube)
        : COLORS.block;

    const geometry = new THREE.BoxGeometry(
        descriptor.width,
        descriptor.height,
        descriptor.depth,
    );

    const material = new THREE.MeshStandardMaterial({
        color,
        metalness: 0.08,
        roughness: 0.5,
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.position.set(descriptor.x, descriptor.y, descriptor.z);

    const edges = new THREE.LineSegments(
        new THREE.EdgesGeometry(geometry),
        new THREE.LineBasicMaterial({ color: 0x273a67, transparent: true, opacity: 0.5 }),
    );
    mesh.add(edges);

    return mesh;
}

async function renderState(state) {
    if (!currentSnapshot?.board || !state) return;

    clearGroup(blockGroup);

    const descriptors = blockDescriptorsFromState(
        state,
        currentSnapshot.board,
    );

    for (const descriptor of descriptors) {
        blockGroup.add(createBlockMesh(descriptor));
    }

    currentDisplayState = state;
}

async function applySnapshot(snapshot, options = {}) {
    const boardChanged = !currentSnapshot || currentSnapshot.level !== snapshot.level;
    currentSnapshot = snapshot;

    if (boardChanged || options.rebuildBoard) {
        buildBoard(snapshot);
        resetCamera(snapshot.board);
    } else {
        buildBoard(snapshot);
    }

    await renderState(snapshot.state);
}

async function loadLevels() {
    const data = await api('/api/levels');
    dom.levelSelect.innerHTML = '';

    for (const level of data.levels) {
        const option = document.createElement('option');
        option.value = level.file;
        const levelNumber = Number(level.file.match(/\d+/)?.[0] || 0);
        option.textContent = `Level ${levelNumber}`;
        dom.levelSelect.appendChild(option);
    }
}

async function loadInitialState() {
    const snapshot = await api('/api/state');
    if (snapshot.level) dom.levelSelect.value = snapshot.level;
    await applySnapshot(snapshot, { rebuildBoard: true });
    setStatus(`Ready — ${snapshot.level}`);
}

async function newGame() {
    if (busy || replaying) return;
    clearMetrics();
    const snapshot = await api('/api/new-game', {
        method: 'POST',
        body: JSON.stringify({ level: dom.levelSelect.value }),
    });
    await applySnapshot(snapshot, { rebuildBoard: true });
    setStatus(`New game — ${snapshot.level}`);
}

async function restartGame({ keepSolution = true } = {}) {
    const snapshot = await api('/api/restart', {
        method: 'POST',
        body: '{}',
    });
    await applySnapshot(snapshot, { rebuildBoard: true });
    if (!keepSolution) clearMetrics();
    setStatus('Level restarted.');
    return snapshot;
}

async function move(action, { replay = false } = {}) {
    if ((busy || replaying) && !replay) return;
    if (currentSnapshot?.lost || currentSnapshot?.won) return;

    const previousState = currentSnapshot?.state;
    const snapshot = await api('/api/move', {
        method: 'POST',
        body: JSON.stringify({ action }),
    });

    if (snapshot.invalid_move) {
        setStatus(snapshot.message, 'error');
        await renderState(previousState);
        currentSnapshot = snapshot;
        return;
    }

    await applySnapshot(snapshot);

    if (snapshot.won) {
        setStatus('You win! The block reached the goal.', 'normal');
    } else {
        setStatus(snapshot.message || `Move: ${action}`);
    }
}

async function animateSearchTrace(trace) {
    if (!trace?.length) return;

    setStatus('Visualizing expanded search states...', 'search');

    for (const step of trace) {
        if (!busy) break;
        dom.expanded.textContent = step.expanded_nodes;
        dom.frontier.textContent = step.frontier_size;
        buildBoard({ board: currentSnapshot.board, state: step.state });
        await renderState(step.state, { animate: false });
        await sleep(TRACE_DELAY_MS);
    }
}

async function solve(algorithm) {
    if (busy || replaying) return;

    setBusy(true, `Running ${algorithm}...`);
    setStatus(`Searching with ${algorithm}...`, 'search');
    dom.algorithm.textContent = algorithm;
    dom.time.textContent = 'Searching...';
    dom.memory.textContent = 'Searching...';
    dom.expanded.textContent = '0';
    dom.frontier.textContent = '0';
    dom.length.textContent = '—';
    dom.cost.textContent = '—';
    dom.path.textContent = 'Searching...';
    dom.replay.disabled = true;

    try {
        const result = await api('/api/solve', {
            method: 'POST',
            body: JSON.stringify({
                algorithm,
                visualize: dom.visualize.checked,
            }),
        });

        if (dom.visualize.checked && result.search_trace?.length) {
            dom.loading.classList.add('hidden');
            await animateSearchTrace(result.search_trace);
        }

        await restartGame({ keepSolution: true });
        updateMetrics(result);
        setStatus(
            result.found
                ? `${algorithm}: solution found. Press Replay Solution.`
                : `${algorithm}: no solution found.`,
            result.found ? 'normal' : 'warning',
        );
    } catch (error) {
        setStatus(`Solver error: ${error.message}`, 'error');
    } finally {
        setBusy(false);
    }
}

async function replaySolution() {
    if (busy || replaying || lastSolution.length === 0) return;

    replaying = true;
    dom.replay.disabled = true;
    dom.solverButtons.forEach(button => button.disabled = true);
    dom.restart.disabled = true;
    dom.newGame.disabled = true;
    dom.levelSelect.disabled = true;

    try {
        await restartGame({ keepSolution: true });
        setStatus('Replaying solution...', 'search');

        for (let index = 0; index < lastSolution.length; index += 1) {
            const action = lastSolution[index];
            setStatus(`Replay ${index + 1}/${lastSolution.length}: ${action}`, 'search');
            await move(action, { replay: true });
            await sleep(REPLAY_DELAY_MS);
        }

        if (currentSnapshot?.won) {
            setStatus('Replay finished — You win!', 'normal');
        } else {
            setStatus('Replay finished.', 'normal');
        }
    } catch (error) {
        setStatus(`Replay error: ${error.message}`, 'error');
    } finally {
        replaying = false;
        dom.replay.disabled = lastSolution.length === 0;
        dom.solverButtons.forEach(button => button.disabled = false);
        dom.restart.disabled = false;
        dom.newGame.disabled = false;
        dom.levelSelect.disabled = false;
    }
}

function bindEvents() {
    dom.newGame.addEventListener('click', () => newGame().catch(handleError));
    dom.restart.addEventListener('click', () => restartGame({ keepSolution: true }).catch(handleError));
    dom.camera.addEventListener('click', () => resetCamera());
    dom.replay.addEventListener('click', () => replaySolution().catch(handleError));

    dom.solverButtons.forEach(button => {
        button.addEventListener('click', () => solve(button.dataset.algorithm));
    });

    window.addEventListener('keydown', event => {
        if (event.target instanceof HTMLSelectElement || event.target instanceof HTMLInputElement) return;

        const actions = {
            ArrowUp: 'UP',
            ArrowDown: 'DOWN',
            ArrowLeft: 'LEFT',
            ArrowRight: 'RIGHT',
            Space: 'SWITCH_CUBE',
        };

        const action = actions[event.code];
        if (!action) return;

        event.preventDefault();
        move(action).catch(handleError);
    });
}

function handleError(error) {
    console.error(error);
    setStatus(error.message || String(error), 'error');
    setBusy(false);
}

async function boot() {
    initializeThree();
    bindEvents();

    try {
        await loadLevels();
        await loadInitialState();
        clearMetrics();
    } catch (error) {
        handleError(error);
    }
}

boot();
