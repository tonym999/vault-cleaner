import { mount } from 'svelte';
import './shadcn.css';
import Probe from './Probe.svelte';

mount(Probe, { target: document.getElementById('probe')! });
