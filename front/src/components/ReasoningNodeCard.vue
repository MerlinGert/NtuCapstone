<template>
  <div
    class="reasoning-node-card"
    :class="cardClasses"
    @click.stop="$emit('select-node', node)"
  >
    <div class="node-meta-row">
      <span class="node-type">{{ node.type || 'Node' }}</span>
      <span v-if="node.source === 'patch'" class="patch-pill">Patch</span>
      <span v-if="node.relation" class="relation-pill">{{ node.relation }}</span>
    </div>
    <div class="node-title" :title="node.label">{{ node.label }}</div>
    <div v-if="node.children && node.children.length" class="node-children">
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
  computed: {
    cardClasses() {
      return {
        'source-user': this.node.source !== 'patch',
        'source-patch': this.node.source === 'patch',
        'type-hypothesis': this.node.type === 'Hypothesis',
        'type-question': this.node.type === 'AnalyticQuestion',
        'type-finding': this.node.type === 'Finding',
        'type-insight': this.node.type === 'Insight',
      }
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

.source-patch.type-insight {
  background: #ffe6ef;
  border-color: #ee8fad;
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
.relation-pill {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  border-radius: 999px;
  padding: 1px 6px;
  font-size: 10px;
  line-height: 16px;
  font-weight: 700;
  white-space: nowrap;
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
  margin-left: auto;
  color: #64748b;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.35);
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
