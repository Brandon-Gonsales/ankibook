<script lang="ts">
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	interface Props {
		open: boolean;
		title: string;
		children: Snippet;
	}

	let { open = $bindable(), title, children }: Props = $props();
	let dialog = $state<HTMLDialogElement | undefined>();

	$effect(() => {
		if (!dialog) return;
		if (open && !dialog.open) dialog.showModal();
		if (!open && dialog.open) dialog.close();
	});

	function onBackdrop(event: MouseEvent) {
		if (event.target === dialog) open = false;
	}
</script>

<!-- Bottom sheet on phones, centred card on wider screens. -->
<dialog bind:this={dialog} onclose={() => (open = false)} onclick={onBackdrop} aria-label={title}>
	<div class="sheet">
		<div class="grip" aria-hidden="true"></div>
		<header>
			<h2>{title}</h2>
			<button class="icon-btn" type="button" onclick={() => (open = false)} aria-label="Cerrar">
				<Icon name="close" />
			</button>
		</header>
		{#if open}
			{@render children()}
		{/if}
	</div>
</dialog>

<style>
	dialog {
		width: 100%;
		max-width: var(--max);
		max-height: 92dvh;
		margin: auto auto 0;
		padding: 0;
		border: 0;
		border-radius: 22px 22px 0 0;
		background: var(--bg);
		color: var(--fg);
		overflow: auto;
	}

	dialog::backdrop {
		background: color-mix(in srgb, var(--ink) 45%, transparent);
	}

	dialog[open] {
		animation: up 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
	}

	.sheet {
		padding: 8px var(--gutter) calc(20px + var(--safe-b));
	}

	.grip {
		width: 40px;
		height: 4px;
		border-radius: 2px;
		background: var(--line);
		margin: 0 auto 4px;
	}

	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 12px;
	}

	h2 {
		font-size: 1.15rem;
	}

	@media (min-width: 640px) {
		dialog {
			margin: auto;
			border-radius: 22px;
		}
		.grip {
			display: none;
		}
	}

	@keyframes up {
		from {
			transform: translateY(24px);
			opacity: 0;
		}
	}
</style>
