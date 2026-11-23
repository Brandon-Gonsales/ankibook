<script lang="ts">
	import { goto } from '$app/navigation';
	import { session, signOut } from '#lib/auth.svelte.ts';
	import { DEV_UID } from '#lib/firebase.ts';
	import { prefs, setMode, setTheme, type StudyMode, type Theme } from '#lib/prefs.svelte.ts';
	import { notifyError } from '#lib/toast.svelte.ts';

	const themes: { value: Theme; label: string }[] = [
		{ value: 'system', label: 'Sistema' },
		{ value: 'light', label: 'Claro' },
		{ value: 'dark', label: 'Oscuro' }
	];

	const modes: { value: StudyMode; label: string; hint: string }[] = [
		{ value: 'base_to_target', label: 'Normal', hint: 'Ves tu idioma y recuerdas el que aprendes.' },
		{ value: 'target_to_base', label: 'Inverso', hint: 'Ves el idioma que aprendes y recuerdas el tuyo.' },
		{ value: 'mixed', label: 'Mixto', hint: 'Cada tarjeta sale en una dirección al azar.' }
	];

	const modeHint = $derived(modes.find((m) => m.value === prefs.mode)?.hint);

	async function logout() {
		try {
			await signOut();
			goto('/login', { replace: true });
		} catch (err) {
			notifyError(err);
		}
	}
</script>

<main class="page">
	<header class="topbar"><h1>Ajustes</h1></header>

	<section class="account">
		{#if session.photo}
			<img src={session.photo} alt="" width="48" height="48" referrerpolicy="no-referrer" />
		{:else}
			<span class="avatar">{(session.name ?? '?').charAt(0).toUpperCase()}</span>
		{/if}
		<div class="row-main">
			<p class="row-title">{session.name ?? 'Usuario'}</p>
			{#if session.email}<p class="row-sub">{session.email}</p>{/if}
		</div>
	</section>

	<h2 class="section-title">Apariencia</h2>
	<div class="segmented" role="group" aria-label="Tema">
		{#each themes as t (t.value)}
			<button aria-pressed={prefs.theme === t.value} onclick={() => setTheme(t.value)}>{t.label}</button>
		{/each}
	</div>

	<h2 class="section-title">Dirección del repaso</h2>
	<div class="segmented" role="group" aria-label="Dirección del repaso">
		{#each modes as m (m.value)}
			<button aria-pressed={prefs.mode === m.value} onclick={() => setMode(m.value)}>{m.label}</button>
		{/each}
	</div>
	<p class="hint muted">{modeHint}</p>

	<h2 class="section-title">Cuenta</h2>
	{#if DEV_UID}
		<p class="hint muted">Modo desarrollo (UID: {DEV_UID}). Quita VITE_DEV_UID para usar Google.</p>
	{:else}
		<button class="btn danger block" onclick={logout}>Cerrar sesión</button>
	{/if}
</main>

<style>
	.account {
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 16px;
		border-radius: 18px;
		background: var(--surface);
		border: 1px solid var(--line);
	}

	.account img,
	.avatar {
		width: 48px;
		height: 48px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.avatar {
		display: grid;
		place-items: center;
		font-weight: 700;
		background: var(--accent);
		color: var(--on-accent);
	}

	.hint {
		font-size: 0.88rem;
		margin-top: 8px;
	}
</style>
