import { mount } from 'svelte';
import './daisy.css';
import Probe from './Probe.svelte';

mount(Probe, { target: document.getElementById('probe')! });
