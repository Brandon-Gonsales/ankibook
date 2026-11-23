import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		sveltekit({
			// SPA: Firebase Auth runs only in the browser.
			adapter: adapter({ fallback: '200.html' })
		})
	],
	server: {
		// Forward API calls to FastAPI in development (avoids CORS).
		proxy: {
			'/api': 'http://localhost:8000'
		}
	}
});
