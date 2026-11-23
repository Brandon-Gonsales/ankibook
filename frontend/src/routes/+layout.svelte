<script lang="ts">
	import '../app.css';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { initAuth, session } from '#lib/auth.svelte.ts';
	import BottomNav from '#lib/components/BottomNav.svelte';
	import Toast from '#lib/components/Toast.svelte';
	import { applyTheme, prefs } from '#lib/prefs.svelte.ts';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();

	initAuth();

	const isLogin = $derived(page.url.pathname === '/login');
	const showNav = $derived(Boolean(session.uid) && !isLogin && !page.url.pathname.startsWith('/review'));

	// Guard: send signed-out users to /login and signed-in users away from it.
	$effect(() => {
		if (!session.ready) return;
		if (!session.uid && !isLogin) goto('/login', { replace: true });
		else if (session.uid && isLogin) goto('/', { replace: true });
	});

	// Keep the browser chrome colour in sync, including OS theme changes.
	$effect(() => {
		void prefs.theme;
		applyTheme();
		const media = matchMedia('(prefers-color-scheme: dark)');
		media.addEventListener('change', applyTheme);
		return () => media.removeEventListener('change', applyTheme);
	});
</script>

{#if !session.ready || (!session.uid && !isLogin)}
	<div class="splash" aria-label="Cargando"><span></span></div>
{:else}
	{@render children()}
	{#if showNav}<BottomNav />{/if}
{/if}
<Toast />

<style>
	.splash {
		min-height: 100dvh;
		display: grid;
		place-items: center;
	}

	.splash span {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		border: 3px solid var(--line);
		border-top-color: var(--accent);
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
