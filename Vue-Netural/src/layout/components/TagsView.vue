<!-- src/layout/components/TagsView.vue -->
<template>
  <div class="tags-view-container" v-if="visitedViews.length > 0">
    <div class="tags-view-wrapper">
      <router-link
        v-for="tag in visitedViews"
        :key="tag.path"
        :to="{ path: tag.path }"
        class="tags-view-item"
        :class="{ active: tag.path === route.path }"
      >
        <span class="tag-dot"></span>
        <span>{{ (tag.meta && tag.meta.title) || tag.name }}</span>
        <el-icon
          v-if="visitedViews.length > 1"
          class="close-icon"
          @click.prevent.stop="closeTag(tag)"
        >
          <Close />
        </el-icon>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Close } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const visitedViews = ref([])

watch(
  () => route.path,
  () => {
    if (route.meta && route.meta.hidden) return
    var exists = visitedViews.value.find(function (v) { return v.path === route.path })
    if (!exists) {
      visitedViews.value.push({
        path: route.path,
        name: route.name,
        meta: route.meta
      })
    }
  },
  { immediate: true }
)

function closeTag(tag) {
  var index = visitedViews.value.findIndex(function (v) { return v.path === tag.path })
  if (index === -1) return
  visitedViews.value.splice(index, 1)
  if (tag.path === route.path && visitedViews.value.length > 0) {
    var last = visitedViews.value[visitedViews.value.length - 1]
    router.push(last.path)
  }
}
</script>

<style scoped>
.tags-view-container {
  height: 36px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  transition: background 0.4s ease, border-color 0.4s ease;
}

.tags-view-wrapper {
  display:100%;
  padding: 0 16px;
  gap: 6px;
  overflow-x: auto;
}

.tags-view-wrapper::-webkit-scrollbar {
  display: none;
}

.tags-view-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 26px;
  padding: 0 10px;
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: none;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: 6px;
  white-space: nowrap;
  transition: all 0.3s ease;
  line-height: 26px;
}

/* 小圆点 */
.tag-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
  transition: background 0.3s ease;
}

.tags-view-item:hover {
  color: var(--text-secondary);
  border-color: var(--border-hover);
  background: var(--bg-card-hover);
}

.tags-view-item:hover .tag-dot {
  background: var(--text-secondary);
}

.tags-view-item.active {
  color: var(--accent);
  border-color: var(--border-accent);
  background: var(--accent-bg);
}

.tags-view-item.active .tag-dot {
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent-glow);
}

.close-icon {
  font-size: 12px;
  border-radius: 50 flex;
  align-items: center;
  height: 1%;
  padding: 1px;
  transition: all 0.2s ease;
  color: var(--text-muted);
}

.close-icon:hover {
  background: var(--danger-bg);
  color: var(--danger);
}
</style>
