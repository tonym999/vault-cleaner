import { mount } from 'svelte';
import './plain.css';
import Probe from './Probe.svelte';

mount(Probe, { target: document.getElementById('probe')! });
