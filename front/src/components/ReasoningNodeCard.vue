<template>
  <div
    class="reasoning-node-card"
    :class="cardClasses"
    @click.stop="$emit('select-node', node)"
  >
    <div class="node-meta-row">
      <span class="node-type">{{ node.type || 'Node' }}</span>
      <span v-if="node.source === 'patch'" class="patch-pill">Patch</span>
      <span class="meta-spacer"></span>
      <span v-if="node.relation" class="relation-pill">{{ node.relation }}</span>
      <button
        v-if="hasChildren"
        class="collapse-btn"
        type="button"
        :aria-label="collapsed ? 'Expand node' : 'Collapse node'"
        @click.stop="collapsed = !collapsed"
      >
        {{ collapsed ? '+' : '-' }}
      </button>
    </div>
    <div class="node-title" :title="node.label">{{ node.label }}</div>
    <div v-if="hasChildren && !collapsed" class="node-children">
      <ReasoningNodeCard
        v-for="child in node.children"
        :key="child.instanceId || child.id"
        :node="child"
        @select-node="$emit('select-node', $event)"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'ReasoningNodeCard',
  props: {
    node: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
      collapsed: this.shouldCollapseByDefault(),
    }
  },
  computed: {
    hasChildren() {
      return Array.isArray(this.node.children) && this.node.children.length > 0
    },
    cardClasses() {
      return {
        'source-user': this.node.source !== 'patch',
        'source-patch': this.node.source === 'patch',
        'type-hypothesis': this.node.type === 'Hypothesis',
        'type-question': this.node.type === 'AnalyticQuestion',
        'type-finding': this.node.type === 'Finding',
      }
    },
  },
  methods: {
    shouldCollapseByDefault() {
      if (this.node.type === 'AnalyticActivity') return true
      const children = Array.isArray(this.node.children) ? this.node.children : []
      return children.length > 0 && children.every((child) => child.type === 'Interaction')
    },
  },
}
</script>

<style scoped>
.reasoning-node-card {
  width: 100%;
  min-width: 0;
  border: 1px solid #d8e0ec;
  border-radius: 7px;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  cursor: pointer;
  padding: 8px;
}

.reasoning-node-card + .reasoning-node-card {
  margin-top: 8px;
}

.source-user.type-hypothesis {
  background: #d9e3ff;
  border-color: #aabce8;
}

.source-user.type-question {
  background: #ffffff;
  border-color: #cbd5e1;
}

.source-patch {
  background: #fff1f5;
  border-color: #f7b7ca;
  box-shadow: 0 1px 3px rgba(190, 24, 93, 0.12);
}

.node-meta-row {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 6px;
  min-width: 0;
}

.node-type,
.patch-pill,
.relation-pill,
.collapse-btn {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  border-radius: 999px;
  font-size: 10px;
  line-height: 16px;
  font-weight: 700;
  white-space: nowrap;
}

.node-type,
.patch-pill,
.relation-pill {
  padding: 1px 6px;
}

.node-type {
  color: #334155;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.45);
}

.patch-pill {
  color: #be185d;
  background: #ffffff;
  border: 1px solid #f9a8d4;
}

.relation-pill {
  margin-right: 6px;
  color: #64748b;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.meta-spacer {
  flex: 1 1 auto;
  min-width: 12px;
}

.collapse-btn {
  justify-content: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 1px solid rgba(148, 163, 184, 0.45);
  background: rgba(255, 255, 255, 0.8);
  color: #475569;
  cursor: pointer;
}

.collapse-btn:hover {
  background: #ffffff;
  border-color: #94a3b8;
}

.node-title {
  color: #111827;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.node-children {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 9px;
  padding: 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.52);
  border: 1px solid rgba(148, 163, 184, 0.28);
}
</style>
