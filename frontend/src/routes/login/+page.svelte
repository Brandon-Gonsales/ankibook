<script lang="ts">
	import { signInWithGoogle } from '#lib/auth.svelte.ts';
	import { firebaseConfigured } from '#lib/firebase.ts';
	import { notifyError } from '#lib/toast.svelte.ts';

	let busy = $state(false);

	async function login() {
		busy = true;
		try {
			await signInWithGoogle();
		} catch (err) {
			notifyError(err);
		} finally {
			busy = false;
		}
	}
</script>

<main>
	<div class="brand">
		<img src="/icon.svg" alt="" width="64" height="64" />
		<h1>AnkiBook</h1>
		<p class="muted">Tus libros de vocabulario,<br />con repaso espaciado.</p>
	</div>

	<div class="bottom">
		{#if firebaseConfigured}
			<button class="btn primary block google" onclick={login} disabled={busy}>
				<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
					<path
						fill="currentColor"
						d="M21.35 11.1H12v2.98h5.38c-.23 1.4-1.64 4.1-5.38 4.1a5.94 5.94 0 0 1 0-11.88c1.84 0 3.07.78 3.78 1.46l2.58-2.48A9.1 9.1 0 0 0 12 2.8a9.2 9.2 0 1 0 0 18.4c5.3 0 8.82-3.73 8.82-8.98 0-.6-.07-1.06-.15-1.52z"
					/>
				</svg>
				{busy ? 'Abriendo Google…' : 'Continuar con Google'}
			</button>
		{:else}
			<p class="note">
				Falta la configuración de Firebase. Copia <code>.env.example</code> a <code>.env</code> en
				<code>frontend/</code> y completa las claves <code>VITE_FIREBASE_*</code>.
			</p>
		{/if}
	</div>
</main>

<style>
	main {
		min-height: 100dvh;
		max-width: 420px;
		margin: 0 auto;
		padding: 0 24px calc(32px + var(--safe-b));
		display: flex;
		flex-direction: column;
	}

	.brand {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		gap: 14px;
	}

	.brand img {
		border-radius: 16px;
	}

	h1 {
		font-size: 2rem;
		letter-spacing: -0.02em;
	}

	.google {
		min-height: 54px;
	}

	.note {
		font-size: 0.9rem;
		color: var(--muted);
		text-align: center;
	}

	code {
		font-size: 0.85em;
		background: var(--surface);
		padding: 1px 5px;
		border-radius: 5px;
	}
</style>
