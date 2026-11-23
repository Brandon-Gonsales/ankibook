<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api, type BookInput } from '#lib/api.ts';
	import BookForm from '#lib/components/BookForm.svelte';
	import DangerButton from '#lib/components/DangerButton.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import Sheet from '#lib/components/Sheet.svelte';
	import { langName } from '#lib/langs.ts';
	import { notify, notifyError } from '#lib/toast.svelte.ts';
	import type { BookDetail, Lection } from '#lib/types.ts';

	const id = $derived(page.params.id ?? '');

	let book = $state<BookDetail | null>(null);
	let editingBook = $state(false);
	let addingLection = $state(false);
	let selected = $state<Lection | null>(null);
	let lectionOpen = $state(false);
	let newName = $state('');
	let rename = $state('');
	let busy = $state(false);

	const lections = $derived(book ? [...book.ankilections].sort((a, b) => a.position - b.position) : []);

	async function load(bookId: string) {
		try {
			book = await api.book(bookId);
		} catch (err) {
			notifyError(err);
			goto('/', { replace: true });
		}
	}

	$effect(() => {
		load(id);
	});

	async function saveBook(data: BookInput) {
		await api.updateBook(id, data);
		editingBook = false;
		await load(id);
	}

	async function deleteBook() {
		try {
			await api.deleteBook(id);
			notify('Libro eliminado');
			goto('/', { replace: true });
		} catch (err) {
			notifyError(err);
		}
	}

	async function addLection(event: SubmitEvent) {
		event.preventDefault();
		const name = newName.trim();
		if (!name) return;
		busy = true;
		try {
			const position = lections.length ? Math.max(...lections.map((l) => l.position)) + 1 : 0;
			const lection = await api.createLection(id, { name, position });
			newName = '';
			addingLection = false;
			goto(`/lections/${lection.id}`);
		} catch (err) {
			notifyError(err);
		} finally {
			busy = false;
		}
	}

	function openLection(lection: Lection) {
		selected = lection;
		rename = lection.name;
		lectionOpen = true;
	}

	async function saveLection(event: SubmitEvent) {
		event.preventDefault();
		if (!selected || !rename.trim()) return;
		busy = true;
		try {
			await api.updateLection(selected.id, { name: rename.trim() });
			lectionOpen = false;
			await load(id);
		} catch (err) {
			notifyError(err);
		} finally {
			busy = false;
		}
	}

	/** Move a lesson and rewrite positions 0..n so ordering stays unambiguous. */
	async function move(lection: Lection, delta: -1 | 1) {
		const order = [...lections];
		const from = order.findIndex((l) => l.id === lection.id);
		const to = from + delta;
		if (to < 0 || to >= order.length) return;
		[order[from], order[to]] = [order[to], order[from]];
		busy = true;
		try {
			await Promise.all(
				order.map((l, index) => (l.position === index ? null : api.updateLection(l.id, { position: index })))
			);
			await load(id);
			selected = lections.find((l) => l.id === lection.id) ?? null;
		} catch (err) {
			notifyError(err);
		} finally {
			busy = false;
		}
	}

	async function deleteLection() {
		if (!selected) return;
		try {
			await api.deleteLection(selected.id);
			lectionOpen = false;
			await load(id);
		} catch (err) {
			notifyError(err);
		}
	}

	async function toggleLibrary() {
		if (!book) return;
		busy = true;
		try {
			if (book.is_added) {
				await api.removeFromLibrary(id);
				notify('Quitado de tus libros');
			} else {
				await api.addToLibrary(id);
				notify('Agregado: ya entra en tus repasos');
			}
			book.is_added = !book.is_added;
		} catch (err) {
			notifyError(err);
		} finally {
			busy = false;
		}
	}

	const selectedIndex = $derived(selected ? lections.findIndex((l) => l.id === selected?.id) : -1);
</script>

<main class="page">
	<header class="topbar">
		<a class="icon-btn" href="/" aria-label="Volver"><Icon name="back" /></a>
		<h1>{book?.title ?? ''}</h1>
		{#if book?.is_owner}
			<button class="icon-btn" onclick={() => (editingBook = true)} aria-label="Editar libro">
				<Icon name="more" />
			</button>
		{/if}
	</header>

	{#if book}
		<p class="meta muted">
			{langName(book.target_lang)} ← {langName(book.base_lang)} · {book.cards_count}
			{book.cards_count === 1 ? 'tarjeta' : 'tarjetas'}
		</p>
		{#if book.description}<p class="desc">{book.description}</p>{/if}

		<div class="book-actions">
			{#if (book.is_owner || book.is_added) && book.cards_count > 0}
				<a class="btn primary block" href={`/review?book=${book.id}`}>
					<Icon name="study" size={18} /> Estudiar libro
				</a>
			{/if}
			{#if !book.is_owner}
				<button class="btn block" class:primary={!book.is_added} onclick={toggleLibrary} disabled={busy}>
					{#if book.is_added}<Icon name="check" size={18} /> En mis libros · Quitar{:else}<Icon name="plus" size={18} /> Agregar a mis libros{/if}
				</button>
			{/if}
		</div>

		<h2 class="section-title">Lecciones</h2>
		{#if lections.length === 0}
			<div class="empty">
				<p>Este libro no tiene lecciones.</p>
				{#if book.is_owner}<p>Toca <strong>+</strong> para añadir una.</p>{/if}
			</div>
		{:else}
			<ul class="list">
				{#each lections as lection, i (lection.id)}
					<li class="lection">
						<a class="row" href={`/lections/${lection.id}`}>
							<span class="num">{i + 1}</span>
							<span class="row-main">
								<span class="row-title">{lection.name}</span>
								<span class="row-sub">
									{lection.cards_count}
									{lection.cards_count === 1 ? 'tarjeta' : 'tarjetas'}
								</span>
							</span>
						</a>
						{#if book.is_owner}
							<button class="icon-btn" onclick={() => openLection(lection)} aria-label={`Opciones de ${lection.name}`}>
								<Icon name="more" />
							</button>
						{:else}
							<span class="chev"><Icon name="chevron" size={18} /></span>
						{/if}
					</li>
				{/each}
			</ul>
		{/if}
	{:else}
		<div class="skeleton"></div>
		<div class="skeleton"></div>
	{/if}
</main>

{#if book?.is_owner}
	<button class="fab" onclick={() => (addingLection = true)} aria-label="Nueva lección">
		<Icon name="plus" size={26} />
	</button>
{/if}

<Sheet bind:open={addingLection} title="Nueva lección">
	<form onsubmit={addLection}>
		<label class="field">
			<span>Nombre</span>
			<!-- svelte-ignore a11y_autofocus -->
			<input class="input" bind:value={newName} required maxlength="255" placeholder="Ej. Saludos" autofocus />
		</label>
		<div class="actions">
			<button class="btn primary block" disabled={busy || !newName.trim()}>Crear lección</button>
		</div>
	</form>
</Sheet>

<Sheet bind:open={lectionOpen} title="Lección">
	<form onsubmit={saveLection}>
		<label class="field">
			<span>Nombre</span>
			<input class="input" bind:value={rename} required maxlength="255" />
		</label>
		<div class="grid-2 reorder">
			<button
				type="button"
				class="btn"
				onclick={() => selected && move(selected, -1)}
				disabled={busy || selectedIndex <= 0}
			>
				<Icon name="up" size={18} /> Subir
			</button>
			<button
				type="button"
				class="btn"
				onclick={() => selected && move(selected, 1)}
				disabled={busy || selectedIndex < 0 || selectedIndex >= lections.length - 1}
			>
				<Icon name="down" size={18} /> Bajar
			</button>
		</div>
		<div class="actions">
			<button class="btn primary block" disabled={busy || !rename.trim()}>Guardar</button>
			<DangerButton label="Eliminar lección" onconfirm={deleteLection} />
		</div>
	</form>
</Sheet>

<Sheet bind:open={editingBook} title="Editar libro">
	{#if book}
		<BookForm {book} submitLabel="Guardar" onsubmit={saveBook} />
		<div class="actions">
			<DangerButton label="Eliminar libro" confirmLabel="Se borra para todos tus compañeros. ¿Seguro?" onconfirm={deleteBook} />
		</div>
	{/if}
</Sheet>

<style>
	.meta {
		font-size: 0.92rem;
		margin-top: -8px;
	}

	.desc {
		margin-top: 8px;
	}

	.lection {
		display: flex;
		align-items: center;
	}

	.num {
		width: 32px;
		height: 32px;
		border-radius: 50%;
		display: grid;
		place-items: center;
		font-size: 0.85rem;
		font-weight: 700;
		color: var(--muted);
		background: var(--surface);
		flex-shrink: 0;
	}

	.row-main {
		display: grid;
	}

	.book-actions {
		display: grid;
		gap: 8px;
		margin-top: 16px;
	}

	.book-actions:empty {
		display: none;
	}

	.reorder {
		margin-bottom: 4px;
	}
</style>
