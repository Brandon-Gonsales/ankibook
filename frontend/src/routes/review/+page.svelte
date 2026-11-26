<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { prefs } from '#lib/prefs.svelte.ts';
	import { formatInterval, formatUntil, previewInterval } from '#lib/srs.ts';
	import { notify, notifyError } from '#lib/toast.svelte.ts';
	import type { Direction, DueCard, Rating, StudySummary } from '#lib/types.ts';

	const BATCH = 50;
	/** New cards added beyond today's limit by "Aprender más". */
	const EXTRA_NEW = 20;
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
	let summary = $state<StudySummary | null>(null);

	// Session stats for the summary screen.
	let correct = $state(0);
	let newLearned = $state(0);
	const newSeen = new Set<string>();
	let minutes = $state(0);
	const startedAt = Date.now();

	const current = $derived(queue[0]);

	/*
	 * /review                → general: due cards + new cards up to today's limit.
	 * /review?more=1         → general, allowing EXTRA_NEW new cards beyond the limit.
	 * /review?book=<id>      → one book: its due cards + all its new cards.
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

	async function fetchMore(extraNew = 0) {
		phase = 'loading';
		try {
			queue = await api.due(BATCH, scope, scoped ? 0 : extraNew);
		} catch (err) {
			notifyError(err);
			queue = [];
		}
		revealed = false;
		direction = pickDirection();
		if (queue.length) {
			phase = 'study';
			return;
		}
		minutes = Math.max(1, Math.round((Date.now() - startedAt) / 60_000));
		summary = await api.summary().catch(() => null);
		phase = 'done';
	}

	fetchMore(page.url.searchParams.get('more') === '1' ? EXTRA_NEW : 0);

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
				if (rating > 1) correct--;
				restore(item);
			}
		});
		return outbox;
	}

	function restore(item: DueCard) {
		queue = [item, ...queue.filter((q) => q.card.id !== item.card.id)];
		if (phase === 'done') phase = 'study';
	}

	async function rate(rating: Rating) {
		if (!current || sending) return;
		const item = $state.snapshot(current) as DueCard;
		const rest = queue.slice(1);
		if (previewInterval(item.progress, rating) * 86_400_000 < REQUEUE_MS) rest.push(item);
		if ((!item.progress || item.progress.state === 'new') && !newSeen.has(item.card.id)) {
			newSeen.add(item.card.id);
			newLearned++;
		}
		submit(item, rating, direction);
		reviewed++;
		if (rating > 1) correct++;
		queue = rest;
		await advance();
	}

	/** Leave the current card for tomorrow, without grading it. */
	async function bury() {
		if (!current || sending) return;
		const item = $state.snapshot(current) as DueCard;
		outbox = outbox.then(async () => {
			try {
				await api.bury(item.card.id);
			} catch (err) {
				notifyError(err);
				restore(item);
			}
		});
		notify('Tarjeta movida a mañana');
		queue = queue.filter((q) => q.card.id !== item.card.id);
		await advance();
	}

	async function advance() {
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
		{#if phase === 'study' && current}
			<button class="icon-btn" onclick={bury} disabled={sending} aria-label="Dejar para mañana" title="Dejar para mañana">
				<Icon name="later" />
			</button>
		{:else}
			<span class="icon-btn" aria-hidden="true"></span>
		{/if}
	</header>

	{#if phase === 'loading'}
		<div class="center"><div class="spinner"></div></div>
	{:else if phase === 'done'}
		{@const canLearnMore = !scoped && (summary?.new_remaining ?? 0) > 0}
		<div class="center done">
			<div class="check"><Icon name="check" size={32} stroke={2.5} /></div>
			<h1>{reviewed ? '¡Sesión completa!' : scoped ? 'Nada por estudiar aquí' : 'Nada pendiente ahora'}</h1>

			{#if reviewed}
				<dl class="stats">
					<div><dt>Tarjetas</dt><dd>{reviewed}</dd></div>
					<div><dt>Aciertos</dt><dd>{Math.round((correct / reviewed) * 100)}%</dd></div>
					<div><dt>Minutos</dt><dd>{minutes}</dd></div>
					<div><dt>Nuevas</dt><dd>{newLearned}</dd></div>
				</dl>
			{:else if scoped}
				<p class="muted">No quedan tarjetas por estudiar aquí ahora.</p>
			{/if}

			{#if summary && !scoped}
				<p class="muted hint">
					{#if summary.next_due}
						Próximo repaso {formatUntil(summary.next_due)}.
					{:else if summary.tomorrow > 0}
						Mañana tienes ~{summary.tomorrow} {summary.tomorrow === 1 ? 'tarjeta' : 'tarjetas'}.
					{/if}
					{#if canLearnMore}
						Te quedan {summary.new_remaining} {summary.new_remaining === 1 ? 'tarjeta nueva' : 'tarjetas nuevas'} por empezar.
					{/if}
				</p>
			{/if}

			<div class="done-actions">
				{#if canLearnMore}
					<button class="btn primary block" onclick={() => fetchMore(EXTRA_NEW)}>Aprender {EXTRA_NEW} más</button>
				{/if}
				<a class="btn block" class:primary={!canLearnMore} href={exitHref}>{scoped ? 'Volver' : 'Volver a mis libros'}</a>
				<button class="btn ghost block" onclick={() => fetchMore()}>Buscar más</button>
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

	.stats {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 8px;
		width: 100%;
		max-width: 360px;
		margin-top: 8px;
	}

	.stats div {
		display: grid;
		gap: 2px;
		padding: 12px 4px;
		border-radius: var(--radius);
		background: var(--surface);
		border: 1px solid var(--line);
	}

	.stats dt {
		font-size: 0.72rem;
		color: var(--muted);
	}

	.stats dd {
		font-size: 1.3rem;
		font-weight: 800;
		font-variant-numeric: tabular-nums;
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
