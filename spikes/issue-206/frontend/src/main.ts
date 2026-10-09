import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';
import { fetchApi } from './lib/api';
import { ReviewSession } from './lib/session.svelte';

const session = new ReviewSession(fetchApi((input, init) => fetch(input, init)));
mount(App, { target: document.getElementById('app')!, props: { session } });
void session.load();
