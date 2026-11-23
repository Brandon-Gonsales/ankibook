<script lang="ts">
	import { api } from '#lib/api.ts';
	import Icon from '#lib/components/Icon.svelte';
	import { langName } from '#lib/langs.ts';
	import { notify, notifyError } from '#lib/toast.svelte.ts';
	import type { Book } from '#lib/types.ts';

	let books = $state<Book[] | null>(null);
	let query = $state('');
	let busy = $state<string | null>(null);

	async function load() {
		try {
			books = await api.explore();
		} catch (err) {
			books ??= [];
			notifyError(err);
		}
	}

	load();

	const visible = $derived.by(() => {
		const q = query.trim().toLowerCase();
		if (!books || !q) return books ?? [];
		return books.filter((b) =>
			[b.title, b.description, langName(b.target_lang)].some((v) => v?.toLowerCase().includes(q))
		);
	});

	async function toggle(book: Book) {
		busy = book.id;
		try {
			if (book.is_added) {
				await api.removeFromLibrary(book.id);
				notify('Quitado de tus libros');
			} else {
				await api.addToLibrary(book.id);
				notify('Agregado a tus libros');
			}
			book.is_added = !book.is_added;
		} catch (err) {
			notifyError(err);
		} finally {
			busy = null;
		}
	}
</script>

<main class="page">
	<header class="topbar"><h1>Explorar</h1></header>
	<p class="intro muted">Todos los libros de la comunidad. Agrega uno para incluirlo en tus repasos.</p>

	{#if books && books.length > 6}
		<input class="input search" type="search" bind:value={query} placeholder="Buscar libro o idioma" />
	{/if}

	{#if books === null}
		<div class="skeleton"></div>
		<div class="skeleton"></div>
		<div class="skeleton"></div>
	{:else if books.length === 0}
		<div class="empty"><p>Todavía no hay libros publicados.</p></div>
	{:else}
		<ul class="list">
			{#each visible as book (book.id)}
				<li class="item">
					<a class="row" href={`/books/${book.id}`}>
						<span class="badge">{book.target_lang.toUpperCase()}</span>
						<span class="row-main">
							<span class="row-title">{book.title}</span>
							<span class="row-sub">
								{langName(book.target_lang)} · {book.cards_count}
								{book.cards_count === 1 ? 'tarjeta' : 'tarjetas'}
							</span>
						</span>
					</a>
					{#if book.is_owner}
						<span class="state">Tuyo</span>
					{:else}
						<button
							class="add"
							class:added={book.is_added}
							onclick={() => toggle(book)}
							disabled={busy === book.id}
							aria-label={book.is_added ? `Quitar ${book.title} de mis libros` : `Agregar ${book.title}`}
						>
							{#if book.is_added}<Icon name="check" size={16} /> Agregado{:else}<Icon name="plus" size={16} /> Agregar{/if}
						</button>
					{/if}
				</li>
			{:else}
				<li class="empty">Sin resultados.</li>
			{/each}
		</ul>
	{/if}
</main>

<style>
	.intro {
		font-size: 0.92rem;
		margin: -8px 0 16px;
	}

	.search {
		margin-bottom: 12px;
	}

	.item {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.item .row {
		flex: 1;
		min-width: 0;
	}

	.row-main {
		display: grid;
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

	.add {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		min-height: 36px;
		padding: 0 12px;
		border-radius: 999px;
		font-size: 0.85rem;
		font-weight: 700;
		background: var(--accent);
		color: var(--on-accent);
		flex-shrink: 0;
	}

	.add.added {
		background: var(--surface);
		color: var(--fg);
		border: 1px solid var(--line);
	}

	.add:disabled {
		opacity: 0.5;
	}

	.state {
		font-size: 0.8rem;
		font-weight: 600;
		color: var(--muted);
		padding: 0 8px;
		flex-shrink: 0;
	}
</style>
