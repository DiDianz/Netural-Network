# Vue-Netural

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Type Support for `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) to make the TypeScript language service aware of `.vue` types.

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

frontend/
├── src/
│   ├── App.vue
│   ├── main.js
│   ├── router/
│   │   └── index.js                  # 路由 + 导航守卫
│   ├── api/
│   │   ├── auth.js                   # 登录接口
│   │   ├── user.js                   # 用户接口
│   │   ├── menu.js                   # 菜单接口
│   │   └── request.js                # Axios 封装
│   ├── stores/
│   │   ├── user.js                   # 用户状态 (Pinia)
│   │   └── permission.js             # 菜单/权限状态
│   ├── layout/
│   │   ├── index.vue                 # 主布局入口
│   │   ├── components/
│   │   │   ├── Navbar.vue            # 顶部导航栏
│   │   │   ├── Sidebar.vue           # 左侧菜单栏
│   │   │   ├── SidebarItem.vue       # 菜单项（递归）
│   │   │   ├── TagsView.vue          # 标签页
│   │   │   └── AppMain.vue           # 内容区
│   │   └── index.scss
│   ├── views/
│   │   ├── login/
│   │   │   └── index.vue             # 登录页面
│   │   ├── prediction/
│   │   │   └── realtime/
│   │   │       └── index.vue         # 实时预测页面
│   │   └── index.vue                 # 首页/工作台
│   ├── composables/
│   │   ├── useSSE.js
│   │   ├── useWebSocket.js
│   │   └── usePredictionStore.js
│   ├── components/
│   │   ├── PredictionChart.vue
│   │   ├── RealtimePanel.vue
│   │   └── ControlPanel.vue
│   ├── utils/
│   │   ├── auth.js                   # Token 工具
│   │   └── sse-client.js
│   └── styles/
│       ├── variables.scss
│       └── index.scss
├── package.json
└── vite.config.js
