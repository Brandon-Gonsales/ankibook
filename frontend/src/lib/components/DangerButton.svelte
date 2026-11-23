<script lang="ts">
	interface Props {
		label: string;
		confirmLabel?: string;
		onconfirm: () => Promise<void>;
	}

	let { label, confirmLabel = 'Toca otra vez para confirmar', onconfirm }: Props = $props();
	let armed = $state(false);
	let busy = $state(false);
	let timer: ReturnType<typeof setTimeout> | undefined;

	async function click() {
		if (!armed) {
			armed = true;
			timer = setTimeout(() => (armed = false), 3000);
			return;
		}
		clearTimeout(timer);
		busy = true;
		try {
			await onconfirm();
		} finally {
			busy = false;
			armed = false;
		}
	}
</script>

<!-- Two-tap delete: no modal on top of a modal, hard to trigger by accident. -->
<button type="button" class="btn danger block" class:armed onclick={click} disabled={busy}>
	{busy ? 'Eliminando…' : armed ? confirmLabel : label}
</button>

<style>
	.armed {
		background: var(--accent);
		color: var(--on-accent);
		border-color: transparent;
	}
</style>
