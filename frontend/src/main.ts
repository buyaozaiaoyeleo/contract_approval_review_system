import { createApp } from 'vue'
import Antd from 'ant-design-vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'

import 'ant-design-vue/dist/reset.css'
import './assets/styles/global.less'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(Antd)

app.mount('#app')