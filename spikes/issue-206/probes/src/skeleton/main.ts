import { mount } from 'svelte';
import './skeleton.css';
import Probe from './Probe.svelte';

mount(Probe, { target: document.getElementById('probe')! });
