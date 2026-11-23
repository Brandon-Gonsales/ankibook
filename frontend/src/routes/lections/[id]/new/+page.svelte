<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';
	import CardForm from '#lib/components/CardForm.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { langName } from '#lib/langs.ts';
	import { notify, notifyError } from '#lib/toast.svelte.ts';
	import type { Book, CardFields, LectionDetail } from '#lib/types.ts';

	const id = $derived(page.params.id ?? '');

	let lection = $state<LectionDetail | null>(null);
	let book = $state<Book | null>(null);
	let added = $state(0);

	$effect(() => {
		const lectionId = id;
		(async () => {
			try {
				lection = await api.lection(lectionId);
				book = await api.book(lection.ankibook_id);
				if (!book.is_owner) goto(`/lections/${lectionId}`, { replace: true });
			} catch (err) {
				notifyError(err);
				goto('/', { replace: true });
			}
		})();
	});

	async function save(data: CardFields) {
		await api.createCard(id, data);
		added++;
		notify('Tarjeta guardada');
		return true; // clear the form for the next one
	}
</script>

<main class="page">
	<header class="topbar">
		<a class="icon-btn" href={`/lections/${id}`} aria-label="Volver"><Icon name="close" /></a>
		<h1>Nueva tarjeta</h1>
		<a class="btn ghost done" href={`/lections/${id}`}>Listo{added ? ` (${added})` : ''}</a>
	</header>

	{#if lection && book}
		<p class="meta muted">{lection.name}</p>
		<CardForm
			baseLabel={langName(book.base_lang)}
			targetLabel={langName(book.target_lang)}
			submitLabel="Guardar y añadir otra"
			onsubmit={save}
		/>
	{:else}
		<div class="skeleton"></div>
	{/if}
</main>

<style>
	.meta {
		font-size: 0.92rem;
		margin: -8px 0 16px;
	}

	.done {
		color: var(--accent);
		padding: 0 12px;
	}
</style>
