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

	// Game dimensions match HTML prototype exactly
	const W = 800;
	const H = 500;
	const BALL_SIZE = 35;
	const BALL_HALF = BALL_SIZE / 2;
	const OBJ_SIZE = 40;
	const OBJ_HALF = OBJ_SIZE / 2;
	const SPEED = 4.4;
	const CORNER_SIZE = 50;
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

	// --- PIXI root — scaled to fit board while preserving 8:5 aspect ratio ---
	const root = new PIXI.Container();
	const _SCALE = Math.min(BOARD_SIZES.width / W, BOARD_SIZES.height / H);
	root.scale.set(_SCALE);
	root.x = Math.round((BOARD_SIZES.width - W * _SCALE) / 2);
	root.y = Math.round((BOARD_SIZES.height - H * _SCALE) / 2);

	const _bg = new PIXI.Graphics();
	_bg.rect(0, 0, W, H);
	_bg.fill({ color: 0x07141d });
	_bg.stroke({ color: 0x2f4553, width: 4 });
	root.addChild(_bg);

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

	// Corner detection — exact HTML logic: 30px proximity zone in each corner
	const getCornerMult = (x: number, y: number): string | null => {
		const s = 30;
		if (x < s && y < s) return cornersState[0].mult; // TL
		if (x > W - s - BALL_SIZE && y < s) return cornersState[1].mult; // TR
		if (x < s && y > H - s - BALL_SIZE) return cornersState[2].mult; // BL
		if (x > W - s - BALL_SIZE && y > H - s - BALL_SIZE) return cornersState[3].mult; // BR
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
			// HTML ranges: x in [100, 700], y in [100, 400]
			const ox = Math.random() * 600 + 100;
			const oy = Math.random() * 300 + 100;
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

	// updateBall — exact copy of HTML Ball.update()
	const updateBall = (ball: BallState) => {
		if (!gameActive) return;

		ball.x += ball.vx;
		ball.y += ball.vy;

		// Corner check first, position-only 30px zone (matches HTML getCornerMult)
		const multStr = getCornerMult(ball.x, ball.y);
		if (multStr !== null && multStr !== 'NONE') {
			const mult = parseFloat(multStr);
			const payout = tumbleValue * mult;
			onCornerHit?.({ payout, multiplier: mult });
			destroyBall(ball);
			endGame(payout);
			return;
		}

		// Two independent ifs — matches HTML exactly (corner hit counts as 2 bounces)
		if (ball.x <= 0 || ball.x >= W - BALL_SIZE) {
			ball.vx *= -1;
			if (onBounce(ball)) return;
		}
		if (!gameActive) return;
		if (ball.y <= 0 || ball.y >= H - BALL_SIZE) {
			ball.vy *= -1;
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
