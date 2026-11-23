<script lang="ts">
	import { goto } from '$app/navigation';
	import { api, type BookInput } from '#lib/api.ts';
	import { session } from '#lib/auth.svelte.ts';
	import BookForm from '#lib/components/BookForm.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Sheet from '#lib/components/Sheet.svelte';
	import { langName } from '#lib/langs.ts';
	import { notifyError } from '#lib/toast.svelte.ts';
	import type { Book } from '#lib/types.ts';

	const DUE_LIMIT = 100;

	let books = $state<Book[] | null>(null);
	let due = $state<number | null>(null);
	let creating = $state(false);

	async function load() {
		try {
			const [list, dueCards] = await Promise.all([api.books(), api.due(DUE_LIMIT)]);
			books = list;
			due = dueCards.length;
		} catch (err) {
			books ??= [];
			notifyError(err);
		}
	}

	load();

	async function create(data: BookInput) {
		const book = await api.createBook(data);
		creating = false;
		goto(`/books/${book.id}`);
	}

	const firstName = $derived(session.name?.split(' ')[0]);
	const dueLabel = $derived(due === null ? '…' : due >= DUE_LIMIT ? `${DUE_LIMIT}+` : String(due));
</script>

<main class="page">
	<header class="topbar">
		<h1>{firstName ? `Hola, ${firstName}` : 'AnkiBook'}</h1>
	</header>

	<a class="study" href="/review" class:idle={due === 0}>
		<div>
			<p class="study-count">{dueLabel}</p>
			<p class="study-label">{due === 0 ? 'Todo al día' : 'tarjetas para repasar'}</p>
		</div>
		<span class="study-go">{due === 0 ? 'Ver' : 'Repasar'}<Icon name="chevron" size={18} /></span>
	</a>

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
