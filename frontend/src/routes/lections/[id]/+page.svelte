<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';
	import { LIMITS } from '#lib/limits.ts';
	import Icon from '#lib/components/Icon.svelte';
	import Sheet from '#lib/components/Sheet.svelte';
	import { langName } from '#lib/langs.ts';
	import { notify, notifyError } from '#lib/toast.svelte.ts';
	import type { Book, CardFields, LectionDetail } from '#lib/types.ts';

	const id = $derived(page.params.id ?? '');

	let lection = $state<LectionDetail | null>(null);
	let book = $state<Book | null>(null);
	let menuOpen = $state(false);
	let bulkOpen = $state(false);
	let bulkText = $state('');
	let busy = $state(false);
	let query = $state('');

	async function load(lectionId: string) {
		try {
			lection = await api.lection(lectionId);
			if (book?.id !== lection.ankibook_id) book = await api.book(lection.ankibook_id);
		} catch (err) {
			notifyError(err);
			goto('/', { replace: true });
		}
	}

	$effect(() => {
		load(id);
	});

	const cards = $derived.by(() => {
		const all = lection?.ankicards ?? [];
		const q = query.trim().toLowerCase();
		if (!q) return all;
		return all.filter((c) => [c.base_text, c.target_1, c.reading].some((v) => v?.toLowerCase().includes(q)));
	});

	/**
	 * One card per line, columns separated by tab (spreadsheet paste), ";" or, as a
	 * last resort, "," (CSV):
	 * base ; target ; reading ; example base ; example target
	 */
	const parsed = $derived.by(() => {
		const valid: CardFields[] = [];
		let invalid = 0;
		for (const raw of bulkText.split(/\r?\n/)) {
			if (!raw.trim()) continue;
			const sep = raw.includes('\t') ? '\t' : raw.includes(';') ? ';' : ',';
			const cols = raw.split(sep).map((c) => c.trim());
			const [base, target, reading, exBase, exTarget] = cols;
			const tooLong =
				base?.length > LIMITS.text ||
				target?.length > LIMITS.text ||
				(reading?.length ?? 0) > LIMITS.reading ||
				(exBase?.length ?? 0) > LIMITS.example ||
				(exTarget?.length ?? 0) > LIMITS.example;
			if (!base || !target || tooLong) {
				invalid++;
				continue;
			}
			valid.push({
				base_text: base,
				target_1: target,
				target_2: null,
				target_3: null,
				reading: reading || null,
				example_base: exBase || null,
				example_target_1: exTarget || null,
				example_target_2: null,
				example_target_3: null
			});
		}
		return { valid, invalid };
	});

	async function importBulk() {
		if (!parsed.valid.length) return;
		busy = true;
		let created = 0;
		try {
			// The API accepts up to LIMITS.bulk cards per request; send big pastes in order.
			for (let i = 0; i < parsed.valid.length; i += LIMITS.bulk) {
				created += (await api.createCards(id, parsed.valid.slice(i, i + LIMITS.bulk))).length;
			}
			notify(`${created} ${created === 1 ? 'tarjeta añadida' : 'tarjetas añadidas'}`);
			bulkText = '';
			bulkOpen = false;
		} catch (err) {
			notifyError(err);
			if (created) notify(`Se añadieron ${created} antes del error. Revisa la lista antes de reintentar.`);
		} finally {
			if (created) await load(id);
			busy = false;
		}
	}

	function openBulk() {
		menuOpen = false;
		bulkOpen = true;
	}
</script>

<main class="page">
	<header class="topbar">
		<a class="icon-btn" href={lection ? `/books/${lection.ankibook_id}` : '/'} aria-label="Volver">
			<Icon name="back" />
		</a>
		<h1>{lection?.name ?? ''}</h1>
	</header>

	{#if lection && book}
		<p class="meta muted">{book.title} · {lection.ankicards.length} {lection.ankicards.length === 1 ? 'tarjeta' : 'tarjetas'}</p>

		{#if lection.ankicards.length > 0}
			{#if book.is_owner || book.is_added}
				<a class="btn primary block study" href={`/review?lection=${lection.id}`}>
					<Icon name="study" size={18} /> Estudiar lección
				</a>
			{:else}
				<p class="hint muted">
					Para estudiar esta lección, <a class="link" href={`/books/${book.id}`}>agrega el libro</a> a tus libros.
				</p>
			{/if}
		{/if}

		{#if lection.ankicards.length > 8}
			<input class="input search" type="search" bind:value={query} placeholder="Buscar tarjeta" />
		{/if}

		{#if lection.ankicards.length === 0}
			<div class="empty">
				<p>Sin tarjetas todavía.</p>
				{#if book.is_owner}<p>Toca <strong>+</strong> para añadir una o pegar varias.</p>{/if}
			</div>
		{:else}
			<ul class="list cards">
				{#each cards as card (card.id)}
					<li>
						<!-- Only the author can open the editor; others just read the list. -->
						<svelte:element this={book.is_owner ? 'a' : 'div'} class="row" href={book.is_owner ? `/cards/${card.id}` : undefined}>
							<span class="row-main pair">
								<span class="row-title">{card.base_text}</span>
								<span class="target">
									{card.target_1}{#if card.reading}<span class="muted"> · {card.reading}</span>{/if}
								</span>
							</span>
							{#if book.is_owner}<span class="chev"><Icon name="chevron" size={18} /></span>{/if}
						</svelte:element>
					</li>
				{:else}
					<li class="empty">Sin resultados.</li>
				{/each}
			</ul>
		{/if}
	{:else}
		<div class="skeleton"></div>
		<div class="skeleton"></div>
		<div class="skeleton"></div>
	{/if}
</main>

{#if book?.is_owner}
	<button class="fab" onclick={() => (menuOpen = true)} aria-label="Añadir tarjetas">
		<Icon name="plus" size={26} />
	</button>
{/if}

<Sheet bind:open={menuOpen} title="Añadir tarjetas">
	<div class="actions">
		<a class="btn primary block" href={`/lections/${id}/new`}><Icon name="edit" size={18} /> Una tarjeta</a>
		<button class="btn block" onclick={openBulk}><Icon name="list" size={18} /> Pegar varias</button>
	</div>
</Sheet>

<Sheet bind:open={bulkOpen} title="Pegar varias tarjetas">
	<p class="hint muted">
		Una tarjeta por línea. Separa con <strong>;</strong> (o coma) o pega columnas desde una hoja de cálculo:<br />
		<code>{book ? langName(book.base_lang) : 'base'} ; {book ? langName(book.target_lang) : 'objetivo'} ; lectura</code>
	</p>
	<label class="field">
		<span class="sr-only">Tarjetas</span>
		<textarea class="input bulk" bind:value={bulkText} rows="8" placeholder={'hola ; こんにちは ; konnichiwa\ngracias ; ありがとう ; arigatou'}></textarea>
	</label>
	<p class="count muted">
		{parsed.valid.length} {parsed.valid.length === 1 ? 'tarjeta lista' : 'tarjetas listas'}{#if parsed.invalid}
			· <span class="bad">{parsed.invalid} {parsed.invalid === 1 ? 'línea incompleta o muy larga' : 'líneas incompletas o muy largas'}</span>{/if}
	</p>
	<div class="actions">
		<button class="btn primary block" onclick={importBulk} disabled={busy || !parsed.valid.length}>
			{busy ? 'Añadiendo…' : `Añadir ${parsed.valid.length || ''}`}
		</button>
	</div>
</Sheet>

<style>
	.meta {
		font-size: 0.92rem;
		margin: -8px 0 16px;
	}

	.search {
		margin-bottom: 12px;
	}

	.study {
		margin-bottom: 16px;
	}

	.link {
		color: var(--accent);
		font-weight: 600;
	}

	.pair {
		display: grid;
	}

	.target {
		font-size: 0.95rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.hint {
		font-size: 0.88rem;
		margin-bottom: 12px;
	}

	code {
		display: inline-block;
		margin-top: 4px;
		font-size: 0.85em;
		background: var(--surface);
		padding: 2px 6px;
		border-radius: 6px;
	}

	.bulk {
		font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
		font-size: 15px;
		min-height: 180px;
	}

	.count {
		font-size: 0.88rem;
		margin: -4px 0 8px;
	}

	.bad {
		color: var(--accent);
	}

	.sr-only {
		position: absolute;
		width: 1px;
		height: 1px;
		overflow: hidden;
		clip: rect(0 0 0 0);
	}
</style>
