import { createApp } from 'vue';
import App from './App.vue';
import Router from './router/index.js';
import './style.css';
import './blockly/generators/index.js';

const app = createApp(App);
app.use(Router);
app.mount('#app');
