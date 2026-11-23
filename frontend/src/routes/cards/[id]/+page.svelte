<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';
	import CardForm from '#lib/components/CardForm.svelte';
	import DangerButton from '#lib/components/DangerButton.svelte';
	import Icon from '#lib/components/Icon.svelte';
	import { langName } from '#lib/langs.ts';
	import { notify, notifyError } from '#lib/toast.svelte.ts';
	import type { Book, Card, CardFields } from '#lib/types.ts';

	const id = $derived(page.params.id ?? '');

	let card = $state<Card | null>(null);
	let book = $state<Book | null>(null);

	$effect(() => {
		const cardId = id;
		(async () => {
			try {
				card = await api.card(cardId);
				const lection = await api.lection(card.ankilection_id);
				book = await api.book(lection.ankibook_id);
				if (!book.is_owner) goto(`/lections/${lection.id}`, { replace: true });
			} catch (err) {
				notifyError(err);
				goto('/', { replace: true });
			}
		})();
	});

	const back = $derived(card ? `/lections/${card.ankilection_id}` : '/');

	async function save(data: CardFields) {
		await api.updateCard(id, data);
		notify('Cambios guardados');
		goto(back);
	}

	async function remove() {
		try {
			await api.deleteCard(id);
			notify('Tarjeta eliminada');
			goto(back, { replace: true });
		} catch (err) {
			notifyError(err);
		}
	}
</script>

<main class="page">
	<header class="topbar">
		<a class="icon-btn" href={back} aria-label="Volver"><Icon name="back" /></a>
		<h1>Editar tarjeta</h1>
	</header>

	{#if card && book}
		<CardForm
			{card}
			baseLabel={langName(book.base_lang)}
			targetLabel={langName(book.target_lang)}
			submitLabel="Guardar cambios"
			onsubmit={save}
		/>
		<div class="actions">
			<DangerButton label="Eliminar tarjeta" onconfirm={remove} />
		</div>
	{:else}
		<div class="skeleton"></div>
		<div class="skeleton"></div>
	{/if}
</main>
