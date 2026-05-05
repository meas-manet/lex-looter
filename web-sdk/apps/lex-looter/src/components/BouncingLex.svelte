<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as PIXI from 'pixi.js';
	import { getContextParent } from 'pixi-svelte';

	import { getContext } from '../game/context';
	import { BOARD_SIZES } from '../game/constants';

	type Props = {
		betAmount?: number;
		highMultMode?: boolean;
		noBoomActive?: boolean;
		onCornerHit?: (data: { payout: number; multiplier: number }) => void;
		onComplete?: (data: { payout: number }) => void;
	};

	const {
		betAmount = 1.0,
		highMultMode = false,
		noBoomActive = false,
		onCornerHit,
		onComplete,
	}: Props = $props();

	const context = getContext();
	const parentCtx = getContextParent();

	const W = BOARD_SIZES.width;
	const H = BOARD_SIZES.height;

	// Match HTML proportions: HTML is 800×500 with 35px ball, scale to board
	const BALL_SIZE = 35;
	const BALL_HALF = BALL_SIZE / 2;
	const OBJ_SIZE = 40;
	const OBJ_HALF = OBJ_SIZE / 2;
	const SPEED = 4.4;
	const CORNER_SIZE = 50;
	const CORNER_DETECT = 30; // matches HTML s=30
	const MAX_BOUNCES = 40;
	const WARMUP = 5;
	const OBJ_HIT_DIST = 35;
	const MAX_OBJECTS = 3;
	const SPAWN_CHANCE = 0.012;

	// --- game state ---
	type BallState = {
		isClone: boolean;
		x: number;
		y: number;
		vx: number;
		vy: number;
		hits: number;
		sprite: PIXI.Sprite;
	};

	type ObjectType = 'boom' | 'minus' | 'sticky' | 'special';
	type ObjectState = { type: ObjectType; x: number; y: number; container: PIXI.Container };

	type CornerState = {
		mult: string;
		boxX: number;
		boxY: number;
		gfx: PIXI.Graphics;
		label: PIXI.Text;
	};

	let balls: BallState[] = [];
	let objects: ObjectState[] = [];
	let tumbleValue = 0;
	let bounceCount = 0;
	let gameActive = false;

	// loaded textures
	let texBall: PIXI.Texture;
	let texClone: PIXI.Texture;
	let texBoom: PIXI.Texture;
	let texMinus: PIXI.Texture;
	let texSticky: PIXI.Texture;
	let texSpecial: PIXI.Texture;

	// --- PIXI root ---
	const root = new PIXI.Container();

	// --- Corners ---
	const cornerDefs = [
		{ boxX: 0, boxY: 0 },
		{ boxX: W - CORNER_SIZE, boxY: 0 },
		{ boxX: 0, boxY: H - CORNER_SIZE },
		{ boxX: W - CORNER_SIZE, boxY: H - CORNER_SIZE },
	];

	const cornersState: CornerState[] = cornerDefs.map((d) => {
		const gfx = new PIXI.Graphics();
		const label = new PIXI.Text({
			text: 'NONE',
			style: { fill: 0x666666, fontSize: 13, fontWeight: 'bold' },
		});
		label.anchor.set(0.5, 0.5);
		root.addChild(gfx);
		root.addChild(label);
		return { mult: 'NONE', ...d, gfx, label };
	});

	// --- HUD ---
	const valText = new PIXI.Text({
		text: '$0.00',
		style: { fill: 0x00e701, fontSize: 26, fontWeight: 'bold' },
	});
	valText.anchor.set(0.5, 0);
	valText.x = W / 2;
	valText.y = 12;
	root.addChild(valText);

	const bounceText = new PIXI.Text({
		text: `0 / ${MAX_BOUNCES} Stealth`,
		style: { fill: 0xb1bad3, fontSize: 14 },
	});
	bounceText.anchor.set(0.5, 0);
	bounceText.x = W / 2;
	bounceText.y = 44;
	root.addChild(bounceText);

	// --- Draw helpers ---

	const drawCorner = (c: CornerState) => {
		let borderColor = 0x2f4553,
			fillColor = 0x1a2c38,
			textColor = 0x666666;
		if (c.mult !== 'NONE') {
			const val = parseFloat(c.mult);
			if (highMultMode) {
				if (val >= 5) {
					borderColor = 0xffd700;
					fillColor = 0x1a1500;
					textColor = 0xffd700;
				} else {
					borderColor = 0x00e701;
					fillColor = 0x082010;
					textColor = 0x00e701;
				}
			} else {
				if (val >= 2) {
					borderColor = 0x00e701;
					fillColor = 0x082010;
					textColor = 0x00e701;
				} else {
					borderColor = 0xff4d4d;
					fillColor = 0x2a0808;
					textColor = 0xff4d4d;
				}
			}
		}
		c.gfx.clear();
		c.gfx.roundRect(c.boxX, c.boxY, CORNER_SIZE, CORNER_SIZE, 4);
		c.gfx.fill({ color: fillColor, alpha: 0.95 });
		c.gfx.stroke({ color: borderColor, width: 2 });
		c.label.text = c.mult;
		c.label.style.fill = textColor;
		c.label.x = c.boxX + CORNER_SIZE / 2;
		c.label.y = c.boxY + CORNER_SIZE / 2;
	};

	const randomizeCorners = () => {
		for (const c of cornersState) {
			if (bounceCount < WARMUP) {
				c.mult = 'NONE';
			} else {
				const r = Math.random() * 100;
				if (highMultMode) {
					if (r < 70) c.mult = 'NONE';
					else if (r < 90) c.mult = (Math.random() * 2 + 2.0).toFixed(1) + 'x';
					else c.mult = (Math.random() * 15 + 5).toFixed(1) + 'x';
				} else {
					if (r < 75) c.mult = 'NONE';
					else if (r < 92) c.mult = (Math.random() * 0.9 + 0.1).toFixed(1) + 'x';
					else c.mult = (Math.random() * 10 + 2).toFixed(1) + 'x';
				}
			}
			drawCorner(c);
		}
	};

	// Corner detection — only fires when ball has crossed BOTH walls simultaneously
	// (i.e. physically reached the corner of the board, not just the zone of one wall).
	const getCornerMult = (ball: BallState): string | null => {
		const hitLeft = ball.x <= 0;
		const hitRight = ball.x >= W - BALL_SIZE;
		const hitTop = ball.y <= 0;
		const hitBottom = ball.y >= H - BALL_SIZE;
		if (hitLeft && hitTop) return cornersState[0].mult; // TL
		if (hitRight && hitTop) return cornersState[1].mult; // TR
		if (hitLeft && hitBottom) return cornersState[2].mult; // BL
		if (hitRight && hitBottom) return cornersState[3].mult; // BR
		return null;
	};

	// --- Ball/object creation ---

	const makeBallSprite = (isClone: boolean): PIXI.Sprite => {
		const s = new PIXI.Sprite(isClone ? texClone : texBall);
		s.width = BALL_SIZE;
		s.height = BALL_SIZE;
		root.addChild(s);
		return s;
	};

	const spawnBall = (isClone = false) => {
		const sprite = makeBallSprite(isClone);
		const ball: BallState = {
			isClone,
			x: W / 2 - BALL_HALF,
			y: H / 2 - BALL_HALF,
			vx: Math.random() > 0.5 ? SPEED : -SPEED,
			vy: Math.random() > 0.5 ? SPEED : -SPEED,
			hits: isClone ? 15 : 999,
			sprite,
		};
		sprite.x = ball.x;
		sprite.y = ball.y;
		balls.push(ball);
	};

	const OBJ_TEXTURES: Record<ObjectType, () => PIXI.Texture> = {
		boom: () => texBoom,
		minus: () => texMinus,
		sticky: () => texSticky,
		special: () => texSpecial,
	};

	const MIN_OBJ_DIST = OBJ_SIZE * 2.5; // minimum centre-to-centre distance between objects

	const findSpawnPosition = (): { ox: number; oy: number } | null => {
		const MAX_ATTEMPTS = 20;
		for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
			const ox = Math.random() * (W - 200) + 100;
			const oy = Math.random() * (H - 200) + 100;
			// Check against every existing object
			const tooClose = objects.some((o) => Math.hypot(ox - o.x, oy - o.y) < MIN_OBJ_DIST);
			if (!tooClose) return { ox, oy };
		}
		return null; // couldn't find a free spot — skip this spawn
	};

	const spawnObj = () => {
		if (!gameActive || objects.length >= MAX_OBJECTS) return;
		const types: ObjectType[] = ['boom', 'minus', 'sticky', 'special'];
		const type = types[Math.floor(Math.random() * types.length)];
		if (type === 'boom' && noBoomActive) return;
		if (type === 'sticky' && highMultMode) return;

		const pos = findSpawnPosition();
		if (!pos) return;
		const { ox, oy } = pos;

		const sprite = new PIXI.Sprite(OBJ_TEXTURES[type]());
		sprite.width = OBJ_SIZE;
		sprite.height = OBJ_SIZE;
		sprite.anchor.set(0.5);
		sprite.x = ox;
		sprite.y = oy;
		root.addChild(sprite);
		objects.push({ type, x: ox, y: oy, container: sprite });
	};

	// --- Destruction ---

	const destroyBall = (ball: BallState) => {
		ball.sprite.destroy();
		balls = balls.filter((b) => b !== ball);
	};

	const destroyObj = (obj: ObjectState) => {
		obj.container.destroy();
		objects = objects.filter((o) => o !== obj);
	};

	const endGame = (payout: number) => {
		gameActive = false;
		onComplete?.({ payout });
	};

	// --- Ball update (matches HTML Ball.update + onBounce logic) ---

	const onBounce = (ball: BallState): boolean => {
		// Returns true if the game ended during this bounce
		if (!ball.isClone) {
			bounceCount++;
			tumbleValue += 0.12 * betAmount;
			bounceText.text = `${bounceCount} / ${MAX_BOUNCES} Stealth`;
			randomizeCorners();
			valText.text = `$${tumbleValue.toFixed(2)}`;
			if (bounceCount >= MAX_BOUNCES) {
				endGame(tumbleValue);
				return true;
			}
		} else {
			ball.hits--;
			tumbleValue += 0.08 * betAmount;
			valText.text = `$${tumbleValue.toFixed(2)}`;
			if (ball.hits <= 0) {
				tumbleValue += 0.5 * betAmount;
				valText.text = `$${tumbleValue.toFixed(2)}`;
				destroyBall(ball);
				if (balls.length === 0) endGame(0);
				return true;
			}
		}
		return false;
	};

	const updateBall = (ball: BallState) => {
		if (!gameActive) return;

		ball.x += ball.vx;
		ball.y += ball.vy;

		// Corner hit: only fires when ball has gone past BOTH walls at the same time.
		// Check BEFORE clamping so out-of-bounds state is still visible.
		const multStr = getCornerMult(ball);
		if (multStr !== null && multStr !== 'NONE') {
			const mult = parseFloat(multStr);
			const payout = tumbleValue * mult;
			onCornerHit?.({ payout, multiplier: mult });
			destroyBall(ball);
			endGame(payout);
			return;
		}

		// Wall bounce — X and Y independent.
		if (ball.x <= 0) {
			ball.x = 0;
			ball.vx = Math.abs(ball.vx);
			if (onBounce(ball)) return;
		} else if (ball.x >= W - BALL_SIZE) {
			ball.x = W - BALL_SIZE;
			ball.vx = -Math.abs(ball.vx);
			if (onBounce(ball)) return;
		}

		if (!gameActive) return;

		if (ball.y <= 0) {
			ball.y = 0;
			ball.vy = Math.abs(ball.vy);
			if (onBounce(ball)) return;
		} else if (ball.y >= H - BALL_SIZE) {
			ball.y = H - BALL_SIZE;
			ball.vy = -Math.abs(ball.vy);
			if (onBounce(ball)) return;
		}

		ball.sprite.x = ball.x;
		ball.sprite.y = ball.y;
	};

	// --- Collision check (mirrors HTML checkCollisions) ---

	const checkCollisions = () => {
		for (let bi = balls.length - 1; bi >= 0; bi--) {
			if (!gameActive) return;
			const b = balls[bi];
			const bcx = b.x + BALL_HALF;
			const bcy = b.y + BALL_HALF;
			for (let oi = objects.length - 1; oi >= 0; oi--) {
				const o = objects[oi];
				if (Math.hypot(bcx - o.x, bcy - o.y) < OBJ_HIT_DIST) {
					if (o.type === 'boom') {
						destroyBall(b);
						destroyObj(o);
						if (balls.length === 0) endGame(0);
						break;
					}
					if (o.type === 'minus') {
						tumbleValue *= 0.5;
						valText.text = `$${tumbleValue.toFixed(2)}`;
						destroyObj(o);
					}
					if (o.type === 'sticky') {
						const payout = tumbleValue;
						destroyBall(b);
						destroyObj(o);
						onCornerHit?.({ payout, multiplier: 1 });
						endGame(payout);
						return;
					}
					if (o.type === 'special') {
						spawnBall(true);
						destroyObj(o);
					}
				}
			}
		}
	};

	// --- Game tick ---
	const tick = () => {
		if (!gameActive) return;
		for (let i = balls.length - 1; i >= 0; i--) updateBall(balls[i]);
		if (gameActive) checkCollisions();
		if (gameActive && Math.random() < SPAWN_CHANCE) spawnObj();
	};

	// Draw initial corners
	for (const c of cornersState) drawCorner(c);

	onMount(async () => {
		const app = context.stateApp.pixiApplication;
		if (!app) return;

		// Load sprite assets
		const loaded = await PIXI.Assets.load([
			'/assets/lex/ball.png',
			'/assets/lex/clone2.png',
			'/assets/lex/boom.png',
			'/assets/lex/50.png',
			'/assets/lex/escape.png',
			'/assets/lex/clone.png',
		]);
		texBall = loaded['/assets/lex/ball.png'];
		texClone = loaded['/assets/lex/clone2.png'];
		texBoom = loaded['/assets/lex/boom.png'];
		texMinus = loaded['/assets/lex/50.png'];
		texSticky = loaded['/assets/lex/escape.png'];
		texSpecial = loaded['/assets/lex/clone.png'];

		// Start game
		gameActive = true;
		spawnBall();
		randomizeCorners();
		app.ticker.add(tick);
	});

	onDestroy(() => {
		const app = context.stateApp.pixiApplication;
		if (app) app.ticker.remove(tick);
		gameActive = false;
		for (const b of balls) b.sprite.destroy();
		for (const o of objects) o.container.destroy();
		balls = [];
		objects = [];
	});

	parentCtx.addToParent(root);
</script>
