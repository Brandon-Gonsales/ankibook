<script lang="ts">
	import { untrack } from 'svelte';
	import { LIMITS } from '#lib/limits.ts';
	import { notifyError } from '#lib/toast.svelte.ts';
	import type { CardFields } from '#lib/types.ts';

	interface Props {
		card?: CardFields;
		baseLabel: string;
		targetLabel: string;
		submitLabel: string;
		/** Return true to clear the form for the next card. */
		onsubmit: (data: CardFields) => Promise<boolean | void>;
	}

	let { card, baseLabel, targetLabel, submitLabel, onsubmit }: Props = $props();

	const empty = (): Record<keyof CardFields, string> => ({
		base_text: '',
		target_1: '',
		target_2: '',
		target_3: '',
		reading: '',
		example_base: '',
		example_target_1: '',
		example_target_2: '',
		example_target_3: ''
	});

	const initial = untrack(() => $state.snapshot(card));
	const f = $state(empty());
	if (initial) for (const key of Object.keys(f) as (keyof CardFields)[]) f[key] = initial[key] ?? '';

	let busy = $state(false);
	let first = $state<HTMLInputElement | undefined>();

	const hasExtra = Boolean(initial?.target_2 || initial?.reading);
	const hasExamples = Boolean(initial?.example_base || initial?.example_target_1);

	/** Trim, drop blanks and shift values left so slot 2 is filled before 3. */
	function ordered(values: string[]): (string | null)[] {
		const kept = values.map((v) => v.trim()).filter(Boolean);
		return [0, 1, 2].map((i) => kept[i] ?? null);
	}

	function payload(): CardFields {
		const [t1, t2, t3] = ordered([f.target_1, f.target_2, f.target_3]);
		const [e1, e2, e3] = ordered([f.example_target_1, f.example_target_2, f.example_target_3]);
		return {
			base_text: f.base_text.trim(),
			target_1: t1 ?? '',
			target_2: t2,
			target_3: t3,
			reading: f.reading.trim() || null,
			example_base: f.example_base.trim() || null,
			example_target_1: e1,
			example_target_2: e2,
			example_target_3: e3
		};
	}

	const valid = $derived(Boolean(f.base_text.trim() && (f.target_1.trim() || f.target_2.trim() || f.target_3.trim())));

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (!valid) return;
		busy = true;
		try {
			const reset = await onsubmit(payload());
			if (reset) {
				Object.assign(f, empty());
				first?.focus();
			}
		} catch (err) {
			notifyError(err);
		} finally {
			busy = false;
		}
	}
</script>

<form onsubmit={submit}>
	<label class="field">
		<span>{baseLabel}</span>
		<input class="input" bind:this={first} bind:value={f.base_text} maxlength={LIMITS.text} required autocomplete="off" />
	</label>
	<label class="field">
		<span>{targetLabel}</span>
		<input class="input" bind:value={f.target_1} maxlength={LIMITS.text} required autocomplete="off" />
	</label>

	<details class="more" open={hasExtra}>
		<summary>Lectura y otras traducciones</summary>
		<label class="field">
			<span>Lectura / pronunciación</span>
			<input class="input" bind:value={f.reading} maxlength={LIMITS.reading} autocomplete="off" placeholder="Ej. こんにちは → konnichiwa" />
		</label>
		<label class="field">
			<span>Traducción 2</span>
			<input class="input" bind:value={f.target_2} maxlength={LIMITS.text} autocomplete="off" />
		</label>
		<label class="field">
			<span>Traducción 3</span>
			<input class="input" bind:value={f.target_3} maxlength={LIMITS.text} autocomplete="off" />
		</label>
	</details>

	<details class="more" open={hasExamples}>
		<summary>Ejemplos</summary>
		<label class="field">
			<span>Ejemplo · {baseLabel.toLowerCase()}</span>
			<input class="input" bind:value={f.example_base} maxlength={LIMITS.example} autocomplete="off" />
		</label>
		<label class="field">
			<span>Ejemplo · {targetLabel.toLowerCase()}</span>
			<input class="input" bind:value={f.example_target_1} maxlength={LIMITS.example} autocomplete="off" />
		</label>
		<label class="field">
			<span>Ejemplo 2</span>
			<input class="input" bind:value={f.example_target_2} maxlength={LIMITS.example} autocomplete="off" />
		</label>
		<label class="field">
			<span>Ejemplo 3</span>
			<input class="input" bind:value={f.example_target_3} maxlength={LIMITS.example} autocomplete="off" />
		</label>
	</details>

	<div class="actions">
		<button class="btn primary block" disabled={busy || !valid}>{busy ? 'Guardando…' : submitLabel}</button>
	</div>
</form>
