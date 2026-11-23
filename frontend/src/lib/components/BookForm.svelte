<script lang="ts">
	import { untrack } from 'svelte';
	import type { BookInput } from '#lib/api.ts';
	import { LANGS } from '#lib/langs.ts';
	import { LIMITS } from '#lib/limits.ts';
	import { notifyError } from '#lib/toast.svelte.ts';
	import type { Book } from '#lib/types.ts';

	interface Props {
		book?: Book;
		submitLabel: string;
		onsubmit: (data: BookInput) => Promise<void>;
	}

	let { book, submitLabel, onsubmit }: Props = $props();

	// Initial values only: the form is re-mounted each time the sheet opens.
	const initial = untrack(() => $state.snapshot(book));
	let title = $state(initial?.title ?? '');
	let description = $state(initial?.description ?? '');
	let target = $state(initial?.target_lang ?? 'en');
	let base = $state(initial?.base_lang ?? 'es');
	let busy = $state(false);

	const sameLang = $derived(target === base);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!title.trim() || sameLang) return;
		busy = true;
		try {
			await onsubmit({
				title: title.trim(),
				description: description.trim() || null,
				target_lang: target,
				base_lang: base
			});
		} catch (err) {
			notifyError(err);
		} finally {
			busy = false;
		}
	}
</script>

<form onsubmit={submit}>
	<label class="field">
		<span>Título</span>
		<!-- svelte-ignore a11y_autofocus -->
		<input class="input" bind:value={title} required maxlength="255" placeholder="Ej. Japonés básico" autofocus={!book} />
	</label>

	<div class="grid-2">
		<label class="field">
			<span>Aprendo</span>
			<select class="input" bind:value={target}>
				{#each LANGS as lang (lang.code)}
					<option value={lang.code}>{lang.name}</option>
				{/each}
			</select>
		</label>
		<label class="field">
			<span>Desde</span>
			<select class="input" bind:value={base}>
				{#each LANGS as lang (lang.code)}
					<option value={lang.code}>{lang.name}</option>
				{/each}
			</select>
		</label>
	</div>
	{#if sameLang}
		<p class="warn">Los idiomas deben ser distintos.</p>
	{/if}

	<label class="field">
		<span>Descripción <small>(opcional)</small></span>
		<textarea class="input" bind:value={description} rows="2" maxlength={LIMITS.description}></textarea>
	</label>

	<div class="actions">
		<button class="btn primary block" disabled={busy || !title.trim() || sameLang}>
			{busy ? 'Guardando…' : submitLabel}
		</button>
	</div>
</form>

<style>
	.warn {
		color: var(--accent);
		font-size: 0.85rem;
		margin: -6px 0 12px;
	}
</style>
