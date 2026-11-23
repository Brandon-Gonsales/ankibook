<script lang="ts">
	import { toast } from '#lib/toast.svelte.ts';
</script>

<div class="toast" class:show={toast.visible} role="status" aria-live="polite">
	{toast.message}
</div>

<style>
	.toast {
		position: fixed;
		left: 50%;
		bottom: calc(var(--nav-h) + var(--safe-b) + 88px);
		transform: translate(-50%, 12px);
		max-width: calc(100% - 32px);
		padding: 12px 18px;
		border-radius: 12px;
		background: var(--ink);
		color: var(--paper);
		font-size: 0.92rem;
		font-weight: 500;
		opacity: 0;
		pointer-events: none;
		transition:
			opacity 0.2s ease,
			transform 0.2s ease;
		z-index: 100;
	}

	.show {
		opacity: 1;
		transform: translate(-50%, 0);
	}
</style>
