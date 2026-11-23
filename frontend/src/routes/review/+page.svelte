<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { prefs } from '#lib/prefs.svelte.ts';
	import { formatInterval, previewInterval } from '#lib/srs.ts';
	import { notifyError } from '#lib/toast.svelte.ts';
	import type { Direction, DueCard, Rating } from '#lib/types.ts';

	const BATCH = 50;
	/** Cards rated into a step shorter than this come back in the same session. */
	const REQUEUE_MS = 20 * 60 * 1000;

	const RATINGS: { value: Rating; label: string }[] = [
		{ value: 1, label: 'Otra vez' },
		{ value: 2, label: 'Difícil' },
		{ value: 3, label: 'Bien' },
		{ value: 4, label: 'Fácil' }
	];

	let queue = $state<DueCard[]>([]);
	let phase = $state<'loading' | 'study' | 'done'>('loading');
	let revealed = $state(false);
	let sending = $state(false);
	let reviewed = $state(0);
	let direction = $state<Direction>('base_to_target');

	const current = $derived(queue[0]);

	/*
	 * /review                → general: only due cards already seen.
	 * /review?book=<id>      → one book: its due cards + its new cards.
	 * /review?lection=<id>   → one lesson: same, for that lesson.
	 */
	const scope = {
		book: page.url.searchParams.get('book') ?? undefined,
		lection: page.url.searchParams.get('lection') ?? undefined
	};
	const scoped = Boolean(scope.book || scope.lection);
	const exitHref = scope.lection ? `/lections/${scope.lection}` : scope.book ? `/books/${scope.book}` : '/';

	function pickDirection(): Direction {
		if (prefs.mode === 'mixed') return Math.random() < 0.5 ? 'base_to_target' : 'target_to_base';
		return prefs.mode;
	}

	async function fetchMore() {
		phase = 'loading';
		try {
			queue = await api.due(BATCH, scope);
		} catch (err) {
			notifyError(err);
			queue = [];
		}
		revealed = false;
		direction = pickDirection();
		phase = queue.length ? 'study' : 'done';
	}

	fetchMore();

	/**
	 * Reviews are sent in the background, one after another, so the next card
	 * shows instantly even on a slow connection. Order is kept so a card that
	 * comes back in the same session is graded on top of its previous review.
	 */
	let outbox: Promise<void> = Promise.resolve();

	function submit(item: DueCard, rating: Rating, dir: Direction): Promise<void> {
		outbox = outbox.then(async () => {
			try {
				const result = await api.review(item.card.id, rating, dir);
				const queued = queue.find((q) => q.card.id === item.card.id);
				if (queued) queued.progress = result.progress;
			} catch (err) {
				// Not saved: undo the step and show the card again.
				notifyError(err);
				reviewed--;
				queue = [item, ...queue.filter((q) => q.card.id !== item.card.id)];
				if (phase === 'done') phase = 'study';
			}
		});
		return outbox;
	}

	async function rate(rating: Rating) {
		if (!current || sending) return;
		const item = $state.snapshot(current) as DueCard;
		const rest = queue.slice(1);
		if (previewInterval(item.progress, rating) * 86_400_000 < REQUEUE_MS) rest.push(item);
		submit(item, rating, direction);
		reviewed++;
		queue = rest;
		revealed = false;
		direction = pickDirection();
		if (!queue.length) {
			// Batch finished: wait for pending saves so the next fetch is accurate.
			sending = true;
			phase = 'loading';
			await outbox;
			sending = false;
			if (!queue.length) await fetchMore();
			else phase = 'study';
		}
	}

	function onkeydown(event: KeyboardEvent) {
		if (phase !== 'study' || event.target instanceof HTMLInputElement) return;
		if (!revealed && (event.key === ' ' || event.key === 'Enter')) {
			event.preventDefault();
			revealed = true;
		} else if (revealed && ['1', '2', '3', '4'].includes(event.key)) {
			rate(Number(event.key) as Rating);
		}
	}

	const front = $derived(current ? (direction === 'base_to_target' ? current.card.base_text : current.card.target_1) : '');
	const answers = $derived.by(() => {
		if (!current) return [];
		const c = current.card;
		if (direction === 'target_to_base') return [c.base_text];
		return [c.target_1, c.target_2, c.target_3].filter((v): v is string => Boolean(v));
	});
	const examples = $derived.by(() => {
		if (!current) return [];
		const c = current.card;
		return [c.example_base, c.example_target_1, c.example_target_2, c.example_target_3].filter(
			(v): v is string => Boolean(v)
		);
	});
	const isNew = $derived(!current?.progress || current.progress.state === 'new');
</script>

<svelte:window {onkeydown} />

<main class="study">
	<header>
		<button class="icon-btn" onclick={() => goto(exitHref)} aria-label="Salir del repaso"><Icon name="close" /></button>
		{#if phase === 'study'}
			<span class="counter" aria-label="Restantes">{queue.length}{queue.length >= BATCH ? '+' : ''}</span>
		{/if}
		<span class="icon-btn" aria-hidden="true"></span>
	</header>

	{#if phase === 'loading'}
		<div class="center"><div class="spinner"></div></div>
	{:else if phase === 'done'}
		<div class="center done">
			<div class="check"><Icon name="check" size={32} stroke={2.5} /></div>
			<h1>{reviewed ? '¡Sesión completa!' : 'Todo al día'}</h1>
			<p class="muted">
				{reviewed
					? `Repasaste ${reviewed} ${reviewed === 1 ? 'tarjeta' : 'tarjetas'}.`
					: scoped
						? 'No quedan tarjetas por estudiar aquí ahora.'
						: 'No tienes repasos pendientes ahora.'}
			</p>
			{#if !scoped}
				<p class="muted hint">Las tarjetas nuevas se estudian desde cada libro o lección.</p>
			{/if}
			<div class="done-actions">
				<a class="btn primary block" href={exitHref}>{scoped ? 'Volver' : 'Volver a mis libros'}</a>
				<button class="btn ghost block" onclick={fetchMore}>Buscar más</button>
			</div>
		</div>
	{:else if current}
		<button
			class="card"
			onclick={() => (revealed = true)}
			disabled={revealed}
			aria-label={revealed ? undefined : 'Mostrar respuesta'}
		>
			<span class="context">
				{current.book_title} · {current.lection_name}
				{#if isNew}<span class="tag">Nueva</span>{/if}
			</span>
			<span class="front">{front}</span>

			{#if revealed}
				<span class="divider"></span>
				<span class="answer">
					{#each answers as answer, i (i)}
						<span class:alt={i > 0}>{answer}</span>
					{/each}
				</span>
				{#if current.card.reading}
					<span class="reading">{current.card.reading}</span>
				{/if}
				{#if examples.length}
					<span class="examples">
						{#each examples as example, i (i)}<span>{example}</span>{/each}
					</span>
				{/if}
			{:else}
				<span class="tap muted">Toca para ver la respuesta</span>
			{/if}
		</button>

		<footer>
			{#if revealed}
				<div class="ratings">
					{#each RATINGS as r (r.value)}
						<button class="rate" class:good={r.value === 3} onclick={() => rate(r.value)} disabled={sending}>
							<span class="rate-label">{r.label}</span>
							<span class="rate-time">{formatInterval(previewInterval(current.progress, r.value))}</span>
						</button>
					{/each}
				</div>
			{:else}
				<button class="btn primary block reveal" onclick={() => (revealed = true)}>Mostrar respuesta</button>
			{/if}
		</footer>
	{/if}
</main>

<style>
	.study {
		max-width: var(--max);
		margin: 0 auto;
		min-height: 100dvh;
		display: flex;
		flex-direction: column;
		padding: 8px var(--gutter) calc(16px + var(--safe-b));
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		min-height: 52px;
	}

	.counter {
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--muted);
	}

	.center {
		flex: 1;
		display: grid;
		place-items: center;
		align-content: center;
		gap: 10px;
		text-align: center;
	}

	.spinner {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		border: 3px solid var(--line);
		border-top-color: var(--accent);
		animation: spin 0.8s linear infinite;
	}

	.check {
		width: 64px;
		height: 64px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		background: var(--accent-soft);
		color: var(--accent);
		margin-bottom: 6px;
	}

	.hint {
		font-size: 0.88rem;
		max-width: 300px;
	}

	.done h1 {
		font-size: 1.5rem;
	}

	.done-actions {
		width: 100%;
		max-width: 320px;
		display: grid;
		gap: 8px;
		margin-top: 20px;
	}

	.card {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 24px 8px;
		text-align: center;
		cursor: pointer;
		overflow-wrap: anywhere;
	}

	.card:disabled {
		cursor: default;
		color: inherit;
	}

	.context {
		font-size: 0.8rem;
		color: var(--muted);
		display: inline-flex;
		align-items: center;
		gap: 8px;
	}

	.tag {
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		padding: 2px 8px;
		border-radius: 999px;
		color: var(--accent);
		background: var(--accent-soft);
	}

	.front {
		font-size: clamp(1.9rem, 8vw, 2.8rem);
		font-weight: 700;
		line-height: 1.2;
		letter-spacing: -0.01em;
	}

	.divider {
		width: 48px;
		height: 2px;
		background: var(--accent);
		border-radius: 1px;
		margin: 6px 0;
	}

	.answer {
		display: grid;
		gap: 4px;
		font-size: clamp(1.5rem, 6.5vw, 2.1rem);
		font-weight: 600;
		color: var(--accent);
	}

	.answer .alt {
		font-size: 0.7em;
		font-weight: 500;
		color: var(--fg);
	}

	.reading {
		font-size: 1.05rem;
		color: var(--muted);
	}

	.examples {
		display: grid;
		gap: 4px;
		margin-top: 12px;
		padding-top: 14px;
		border-top: 1px solid var(--line);
		font-size: 0.95rem;
		color: var(--muted);
		width: 100%;
		max-width: 420px;
	}

	.tap {
		font-size: 0.85rem;
		margin-top: 24px;
	}

	footer {
		padding-top: 8px;
	}

	.reveal {
		min-height: 56px;
		font-size: 1.05rem;
	}

	.ratings {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 8px;
	}

	.rate {
		min-height: 64px;
		border-radius: var(--radius);
		background: var(--surface);
		border: 1px solid var(--line);
		display: grid;
		align-content: center;
		gap: 2px;
		transition: transform 0.08s ease;
	}

	.rate:active {
		transform: scale(0.96);
	}

	.rate:disabled {
		opacity: 0.5;
	}

	.rate.good {
		background: var(--accent);
		border-color: transparent;
		color: var(--on-accent);
	}

	.rate-label {
		font-weight: 700;
		font-size: 0.9rem;
	}

	.rate-time {
		font-size: 0.75rem;
		opacity: 0.75;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
