<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, type BookInput } from '#lib/api.ts';
	import { session } from '#lib/auth.svelte.ts';
	import BookForm from '#lib/components/BookForm.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Sheet from '#lib/components/Sheet.svelte';
	import { langName } from '#lib/langs.ts';
	import { formatUntil } from '#lib/srs.ts';
	import { notifyError } from '#lib/toast.svelte.ts';
	import type { Book, BookProgress, StudySummary } from '#lib/types.ts';

	let books = $state<Book[] | null>(null);
	let summary = $state<StudySummary | null>(null);
	let creating = $state(false);

	async function load() {
		try {
			[books, summary] = await Promise.all([api.books(), api.summary()]);
		} catch (err) {
			books ??= [];
			notifyError(err);
		}
	}

	const today = $derived(summary ? summary.due_now + summary.new_today : null);
	const progressByBook = $derived(new Map<string, BookProgress>(summary?.books.map((b) => [b.book_id, b]) ?? []));

	function plural(n: number, one: string, many: string): string {
		return `${n} ${n === 1 ? one : many}`;
	}

	load();

	async function create(data: BookInput) {
		const book = await api.createBook(data);
		creating = false;
		goto(`/books/${book.id}`);
	}

	const firstName = $derived(session.name?.split(' ')[0]);
</script>

<main class="page">
	<header class="topbar">
		<h1>{firstName ? `Hola, ${firstName}` : 'AnkiBook'}</h1>
	</header>

	{#if summary === null || today === null}
		<div class="study">
			<div>
				<p class="study-count">…</p>
				<p class="study-label">Preparando tu día</p>
			</div>
		</div>
	{:else if today > 0}
		<a class="study" href="/review">
			<div>
				<p class="study-count">{today}</p>
				<p class="study-label">
					para hoy · {plural(summary.due_now, 'repaso', 'repasos')} · {plural(summary.new_today, 'nueva', 'nuevas')}
				</p>
			</div>
			<span class="study-go">Repasar<Icon name="chevron" size={18} /></span>
		</a>
	{:else}
		<div class="study idle">
			<div class="idle-main">
				{#if summary.books.length === 0}
					<p class="idle-title">Nada que estudiar aún</p>
					<p class="study-label">Crea un libro o agrega uno desde Explorar.</p>
				{:else}
					<p class="idle-title">
						<span class="done-dot"><Icon name="check" size={16} stroke={3} /></span>
						{summary.reviews_today > 0 ? 'Hoy completado' : 'Nada pendiente ahora'}
					</p>
					<p class="study-label">
						{#if summary.next_due}
							Próximo repaso {formatUntil(summary.next_due)}
						{:else if summary.tomorrow > 0}
							Mañana: ~{plural(summary.tomorrow, 'tarjeta', 'tarjetas')}
						{:else}
							No hay repasos programados.
						{/if}
						{#if summary.reviews_today > 0}· {plural(summary.reviews_today, 'repaso', 'repasos')} hoy{/if}
					</p>
				{/if}
			</div>
			{#if summary.new_remaining > 0}
				<a class="btn primary more" href="/review?more=1">Aprender más</a>
			{/if}
		</div>
	{/if}

	<h2 class="section-title">Mis libros</h2>

	{#if books === null}
		<div class="skeleton"></div>
		<div class="skeleton"></div>
	{:else if books.length === 0}
		<div class="empty">
			<Icon name="book" size={36} stroke={1.5} />
			<p>Aún no tienes libros.</p>
			<p>Toca <strong>+</strong> para crear uno o busca en <a class="link" href="/explore">Explorar</a>.</p>
		</div>
	{:else}
		<ul class="list">
			{#each books as book (book.id)}
				<li>
					<a class="row" href={`/books/${book.id}`}>
						<span class="badge">{book.target_lang.toUpperCase()}</span>
						<span class="row-main">
							<span class="row-title">{book.title}{#if !book.is_owner}<span class="tag">Agregado</span>{/if}</span>
							<span class="row-sub">
								{langName(book.target_lang)} · {book.lections_count}
								{book.lections_count === 1 ? 'lección' : 'lecciones'} · {book.cards_count}
								{book.cards_count === 1 ? 'tarjeta' : 'tarjetas'}
							</span>
							{#if progressByBook.get(book.id)?.total}
								{@const p = progressByBook.get(book.id)!}
								<span
									class="progress"
									role="img"
									aria-label={`${p.learned} aprendidas, ${p.learning} aprendiendo, ${p.new} nuevas`}
								>
									<span class="bar learned" style:width={`${(p.learned / p.total) * 100}%`}></span>
									<span class="bar learning" style:width={`${(p.learning / p.total) * 100}%`}></span>
								</span>
								<span class="progress-label">
									{p.learned} de {p.total} aprendidas{#if p.learning} · {p.learning} aprendiendo{/if}
								</span>
							{/if}
						</span>
						<span class="chev"><Icon name="chevron" size={18} /></span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</main>

<button class="fab" onclick={() => (creating = true)} aria-label="Nuevo libro">
	<Icon name="plus" size={26} />
</button>

<Sheet bind:open={creating} title="Nuevo libro">
	<BookForm submitLabel="Crear libro" onsubmit={create} />
</Sheet>

<style>
	.study {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 16px;
		padding: 20px;
		border-radius: 20px;
		background: var(--accent);
		color: var(--on-accent);
	}

	.study.idle {
		background: var(--surface);
		color: var(--fg);
		border: 1px solid var(--line);
	}

	.study-count {
		font-size: 2.5rem;
		font-weight: 800;
		line-height: 1;
		letter-spacing: -0.03em;
	}

	.study-label {
		margin-top: 4px;
		font-size: 0.92rem;
		opacity: 0.85;
	}

	.study-go {
		display: inline-flex;
		align-items: center;
		gap: 2px;
		font-weight: 700;
	}

	.idle-main {
		min-width: 0;
	}

	.idle-title {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 1.2rem;
		font-weight: 800;
	}

	.done-dot {
		display: grid;
		place-items: center;
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--accent-soft);
		color: var(--accent);
		flex-shrink: 0;
	}

	.more {
		flex-shrink: 0;
		white-space: nowrap;
	}

	.progress {
		display: flex;
		height: 6px;
		margin-top: 8px;
		border-radius: 999px;
		overflow: hidden;
		background: var(--line);
	}

	.bar.learned {
		background: var(--accent);
	}

	.bar.learning {
		background: color-mix(in srgb, var(--accent) 40%, transparent);
	}

	.progress-label {
		margin-top: 4px;
		font-size: 0.78rem;
		color: var(--muted);
	}

	.badge {
		display: grid;
		place-items: center;
		width: 44px;
		height: 44px;
		border-radius: 12px;
		background: var(--accent-soft);
		color: var(--accent);
		font-weight: 800;
		font-size: 0.85rem;
		flex-shrink: 0;
	}

	.row-main {
		display: grid;
	}

	.tag {
		margin-left: 8px;
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		padding: 2px 7px;
		border-radius: 999px;
		vertical-align: 2px;
		color: var(--accent);
		background: var(--accent-soft);
	}

	.link {
		color: var(--accent);
		font-weight: 600;
	}

	.empty :global(svg) {
		color: var(--line);
		margin-bottom: 8px;
	}
</style>
