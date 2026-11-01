<template>
  <section
    v-if="agent"
    class="character-panel game-panel"
    :class="{ 'profile-expanded': expanded }"
    aria-label="Inhabitant profile"
    data-testid="inhabitant-profile"
  >
    <div class="profile-top">
      <span class="eyebrow">A LITTLE LIFE</span>
      <div class="profile-window-actions">
        <GameButton
          v-if="expanded"
          label="Back to world"
          :icon="Minimize2"
          @click="store.profileExpanded = false"
        />
        <GameButton
          v-else
          label="Open full screen"
          :icon="Maximize2"
          icon-only
          @click="store.profileExpanded = true"
        />
        <GameButton
          label="Close profile"
          :icon="X"
          icon-only
          @click="
            store.profileExpanded = false;
            store.selectedId = null;
          "
        />
      </div>
    </div>
    <header class="character-heading">
      <div
        class="portrait"
        :style="{ '--person-color': inhabitantColor(agent.id) }"
      >
        <img
          :src="assetUrl('villager-portrait.png')"
          alt=""
        /><span :class="{ 'is-thinking': thinking }" />
      </div>
      <div>
        <h2>{{ agent.name }}</h2>
        <p>
          <span class="status-dot" />{{
            thinking ? "Thinking…" : activityLabel(agent, store.world?.status === "running")
          }}
        </p>
        <small
          >{{ agent.driver === "scripted" ? "A curious wanderer" : "AI inhabitant" }} ·
          {{ formatAge(agent.body.ageSeconds) }} old</small
        >
      </div>
    </header>
    <div
      v-if="!expanded"
      class="character-actions"
    >
      <GameButton
        v-if="!expanded"
        :label="store.followId === agent.id ? 'Following' : 'Follow along'"
        :icon="Eye"
        :active="store.followId === agent.id"
        @click="store.followId = store.followId === agent.id ? null : agent.id"
      /><GameButton
        v-if="!expanded"
        label="Find in world"
        :icon="Focus"
        icon-only
        @click="emit('focus')"
      />
    </div>
    <div class="needs-grid">
      <div
        v-for="metric in metrics"
        :key="metric.key"
        class="need"
      >
        <component
          :is="metric.icon"
          :size="14"
          :style="{ color: metric.color }"
        /><span>{{ metric.label }}</span
        ><strong>{{ Math.round(agent.body[metric.key]) }}<small>%</small></strong>
        <div class="need-track">
          <i :style="{ width: `${Math.max(0, Math.min(100, agent.body[metric.key]))}%`, background: metric.color }" />
        </div>
      </div>
    </div>
    <aside
      v-if="expanded"
      class="reader-summary"
      aria-label="Inhabitant overview"
    >
      <span class="eyebrow">HERE & NOW</span>
      <dl>
        <div>
          <dt>Name</dt>
          <dd>{{ agent.selfNamed ? "Self chosen" : agent.parentNamed ? "Parent chosen" : "Placeholder" }}</dd>
        </div>
        <div>
          <dt>Health</dt>
          <dd>{{ agent.body.health.toFixed(1) }}%</dd>
        </div>
        <div>
          <dt>Stress</dt>
          <dd>{{ agent.body.stress.toFixed(1) }}%</dd>
        </div>
        <div>
          <dt>Injury</dt>
          <dd>{{ agent.body.injury.toFixed(1) }}%</dd>
        </div>
        <div>
          <dt>Growth</dt>
          <dd>{{ Math.round(agent.body.growth * 100) }}%</dd>
        </div>
      </dl>
      <p>World time {{ formatWorldTime(cutoff) }}</p>
      <p>Only their own memories and conversations within earshot appear here.</p>
      <p>Mind shows shared plans, observations, tools, and recorded outcomes.</p>
    </aside>
    <nav
      class="profile-tabs"
      aria-label="Inhabitant information"
    >
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: store.profileTab === tab.key }"
        :aria-pressed="store.profileTab === tab.key"
        @click="
          store.profileTab = tab.key;
          store.profileExpanded = true;
        "
      >
        <component
          :is="tab.icon"
          :size="15"
        />{{ tab.label
        }}<span
          v-if="tab.key === 'mind' && thinking"
          class="tab-pulse"
        />
      </button>
    </nav>
    <div
      v-if="expanded"
      class="profile-reader-toolbar"
    >
      <label class="profile-search">
        <Search :size="17" />
        <AppInputText
          v-model="query"
          type="search"
          placeholder="Search loaded records…"
          aria-label="Search inhabitant records"
        />
      </label>
      <GameButton
        :label="liveUpdates ? 'Pause updates' : 'Resume updates'"
        :icon="liveUpdates ? Pause : Radio"
        :active="!liveUpdates"
        @click="liveUpdates = !liveUpdates"
      />
      <span role="status"
        >{{ resultCount }} {{ query.trim() ? "matching" : "loaded" }} records ·
        {{ liveUpdates ? "Updating live" : "Updates paused" }}</span
      >
    </div>
    <div
      ref="content"
      class="profile-content"
      tabindex="0"
      :aria-label="`${tabs.find((tab) => tab.key === store.profileTab)?.label} records`"
    >
      <p
        v-if="expanded"
        class="profile-record-scope"
      >
        {{ store.profileTab === "mind" ? "Latest 20 decisions" : "Latest 100 records"
        }}{{ store.replayTick !== null ? " at this replay time" : "" }}. Search applies to loaded records.
      </p>
      <p
        v-if="query.trim() && !resultCount && !loading"
        class="profile-empty"
      >
        No matching records. Try another search.
      </p>
      <p
        v-if="error"
        role="alert"
        class="profile-error"
      >
        {{ error }}
      </p>
      <p
        v-if="loading && !profile"
        class="profile-empty"
      >
        Opening their story…
      </p>
      <template v-if="store.profileTab === 'chat'">
        <div class="section-intro">
          <h3>Within earshot</h3>
          <span><MessageCircle :size="12" />Local conversation</span>
        </div>
        <p
          v-if="!messages.length && !loading"
          class="profile-empty"
        >
          A quiet moment.<br />Conversations will appear here as they happen.
        </p>
        <article
          v-for="message in messages"
          :key="message.id"
          class="chat-message"
          :class="{ own: message.speakerId === agent.id }"
          data-testid="conversation-message"
        >
          <div class="message-meta">
            <span class="message-author"
              ><i
                :style="{ background: inhabitantColor(message.speakerId) }"
                aria-hidden="true"
              />{{ message.speakerName }}</span
            ><time>{{ formatWorldTime(message.tick) }}</time>
          </div>
          <p>{{ message.text }}</p>
        </article>
        <p class="quiet-note"><Ear :size="13" />Only messages they said or could hear.</p>
      </template>
      <template v-if="store.profileTab === 'memories'">
        <div class="section-intro">
          <h3>Things they remember</h3>
          <span>{{ memories.length }} memories</span>
        </div>
        <p
          v-if="!memories.length && !loading"
          class="profile-empty"
        >
          Nothing tucked away yet.<br />Their own memories will grow as they explore.
        </p>
        <article
          v-for="memory in memories"
          :key="memory.id"
          class="memory-card"
        >
          <span class="memory-flower">✿</span>
          <p>{{ memory.text }}</p>
          <footer>
            <time>{{ formatWorldTime(memory.tick) }}</time
            ><span>{{ Math.round(memory.confidence * 100) }}% confident</span>
          </footer>
        </article>
      </template>
      <template v-if="store.profileTab === 'history'">
        <div class="section-intro">
          <h3>A story in little moments</h3>
          <span>Life history</span>
        </div>
        <div class="life-stats">
          <div>
            <span>Health</span><strong>{{ agent.body.health.toFixed(1) }}%</strong>
          </div>
          <div>
            <span>Growth</span><strong>{{ Math.round(agent.body.growth * 100) }}%</strong>
          </div>
          <div>
            <span>Stress</span><strong>{{ agent.body.stress.toFixed(1) }}%</strong>
          </div>
          <div>
            <span>Injury</span><strong>{{ agent.body.injury.toFixed(1) }}%</strong>
          </div>
          <div>
            <span>Wear</span><strong>{{ agent.body.wear.toFixed(4) }}</strong>
          </div>
          <div>
            <span>Repair trait</span><strong>{{ agent.body.repairTrait.toFixed(2) }}×</strong>
          </div>
          <div>
            <span>Strength trait</span><strong>{{ agent.body.strengthTrait.toFixed(2) }}×</strong>
          </div>
          <div>
            <span>Metabolism trait</span><strong>{{ agent.body.metabolismTrait.toFixed(2) }}×</strong>
          </div>
        </div>
        <p
          v-if="agent.parents.length"
          class="parent-note"
        >
          Parents: {{ agent.parents.map(parentName).join(" & ") }}
        </p>
        <p
          v-if="!history.length && !loading"
          class="profile-empty"
        >
          Their story is just beginning.
        </p>
        <article
          v-for="event in history"
          :key="event.id"
          class="life-event"
        >
          <span class="timeline-dot" />
          <div>
            <time>{{ formatWorldTime(event.tick) }}</time>
            <p>{{ describeWorldEvent(event, store.displayState) }}</p>
          </div>
        </article>
      </template>
      <template v-if="store.profileTab === 'mind'">
        <div class="section-intro">
          <h3>Behind the next little step</h3>
          <span
            v-if="thinking"
            class="thinking-label"
            ><i />Thinking live</span
          >
        </div>
        <p
          v-if="!decisions.length && !loading"
          class="profile-empty"
        >
          {{
            agent.driver === "scripted"
              ? "This inhabitant follows a scripted wandering routine. Enable Pydantic AI to see shared plans and live tool activity."
              : "No model session has started yet. Decisions will appear here as they happen."
          }}
        </p>
        <GameButton
          v-if="agent.driver === 'scripted'"
          label="Agent settings"
          :icon="Settings2"
          @click="emit('settings')"
        />
        <article
          v-for="decision in decisions"
          :key="decision.id"
          class="decision-card"
        >
          <header>
            <span class="session-marker"><Brain :size="14" /></span
            ><strong>{{ decision.status === "thinking" ? "Considering their next step…" : "A decision" }}</strong
            ><span
              class="decision-status"
              :class="decision.status"
              >{{ decision.status }}</span
            >
          </header>
          <time>{{ formatWorldTime(decision.tick) }}</time>
          <details class="observation">
            <summary>
              What they could see <span>{{ decision.observation.visibleObjects?.length ?? 0 }} nearby things</span>
            </summary>
            <ul>
              <li
                v-for="object in decision.observation.visibleObjects"
                :key="object.id"
              >
                {{ object.name }} <small>{{ object.material }}</small>
              </li>
            </ul>
            <details>
              <summary>Full observation</summary>
              <pre>{{ JSON.stringify(decision.observation, null, 2) }}</pre>
            </details>
          </details>
          <div
            v-for="(trace, index) in decision.trace"
            :key="index"
            class="tool-trace"
            :class="{ 'shared-plan': trace.tool === 'share_plan', failed: Boolean(trace.error) }"
          >
            <span class="trace-symbol"
              ><Sparkles
                v-if="trace.tool === 'share_plan'"
                :size="13" /><Search
                v-else
                :size="13"
            /></span>
            <div>
              <small>{{ toolLabel(trace.tool) }}</small>
              <p v-if="trace.tool === 'share_plan'">{{ trace.arguments.text }}</p>
              <p v-else-if="trace.error">{{ trace.error }}</p>
              <details v-else>
                <summary>{{ toolSummary(trace) }}</summary>
                <pre>{{ JSON.stringify({ arguments: trace.arguments, result: trace.result }, null, 2) }}</pre>
              </details>
            </div>
          </div>
          <p
            v-if="decision.result?.message"
            class="shared-message"
          >
            “{{ decision.result.message }}”
          </p>
          <div
            v-if="decision.result"
            class="chosen-action"
          >
            <ArrowUpRight :size="14" /><span
              >Chose to <strong>{{ decision.result.action.kind }}</strong></span
            >
          </div>
          <details
            v-if="decision.result"
            class="observation"
          >
            <summary>Action and outcome details</summary>
            <pre>{{ JSON.stringify(decision.result, null, 2) }}</pre>
          </details>
          <p
            v-if="decision.error"
            class="profile-error"
          >
            {{ decision.error }}
          </p>
        </article>
        <p class="quiet-note">
          Shared plans, observations, tools, and outcomes are saved. Private model reasoning is not recorded.
        </p>
      </template>
    </div>
    <footer class="profile-footer">
      <span
        ><span class="status-dot" />{{
          store.replayTick === null ? "Their story, live" : "A moment from their past"
        }}</span
      ><BookOpen :size="14" />Saved in world history
    </footer>
  </section>
</template>

<script setup lang="ts">
  import AppInputText from "@/components/ui/AppInputText.vue";
  import { usePolling } from "@/composables/usePolling";
  import { worldsApi } from "@/features/worlds/api";
  import {
    activityLabel,
    assetUrl,
    describeWorldEvent,
    formatAge,
    formatWorldTime,
    inhabitantColor,
  } from "@/features/worlds/presentation";
  import type { BodyState, InhabitantProfile, ToolTrace } from "@/types/worlds/WorldInterface";
  import { getFirstApiErrorMessage } from "@/utils/errorHandling";
  import GameButton from "@/views/Worlds/GameButton.vue";
  import { useWorldsStore } from "@/views/Worlds/worldsStore";
  import {
    ArrowUpRight,
    BookOpen,
    Brain,
    Droplets,
    Ear,
    Eye,
    Focus,
    Heart,
    Maximize2,
    MessageCircle,
    Minimize2,
    Pause,
    Radio,
    Search,
    Settings2,
    Sparkles,
    Utensils,
    X,
    Zap,
  } from "@lucide/vue";
  import { computed, onBeforeUnmount, ref, watch } from "vue";

  defineProps<{ expanded?: boolean }>();
  const emit = defineEmits<{ focus: []; settings: [] }>();
  const store = useWorldsStore();
  const agent = computed(() => store.selectedInhabitant);
  const profile = ref<InhabitantProfile | null>(null);
  const loading = ref(false);
  const error = ref("");
  const query = ref("");
  const liveUpdates = ref(true);
  const content = ref<HTMLElement>();
  let generation = 0,
    disposed = false;
  let seekTimer: ReturnType<typeof setTimeout> | undefined;
  const cutoff = computed(() => store.displayState?.tick ?? 0);
  function matches(value: string) {
    return value.toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase());
  }
  const messages = computed(
    () =>
      profile.value?.messages.filter(
        (entry) => entry.tick <= cutoff.value && matches(`${entry.speakerName} ${entry.text}`)
      ) ?? []
  );
  const memories = computed(
    () => profile.value?.memories.filter((entry) => entry.tick <= cutoff.value && matches(entry.text)) ?? []
  );
  const history = computed(
    () =>
      profile.value?.history.filter(
        (entry) => entry.tick <= cutoff.value && matches(describeWorldEvent(entry, store.displayState))
      ) ?? []
  );
  const decisions = computed(
    () => profile.value?.decisions.filter((entry) => entry.tick <= cutoff.value && matches(JSON.stringify(entry))) ?? []
  );
  const resultCount = computed(
    () =>
      ({
        chat: messages.value.length,
        memories: memories.value.length,
        history: history.value.length,
        mind: decisions.value.length,
      })[store.profileTab]
  );
  const thinking = computed(
    () => profile.value?.decisions.some((entry) => entry.tick <= cutoff.value && entry.status === "thinking") ?? false
  );
  const metrics: {
    key: keyof Pick<BodyState, "food" | "water" | "energy">;
    label: string;
    icon: typeof Heart;
    color: string;
  }[] = [
    { key: "food", label: "Food", icon: Utensils, color: "#e7ae70" },
    { key: "water", label: "Water", icon: Droplets, color: "#83bdcd" },
    { key: "energy", label: "Energy", icon: Zap, color: "#95bc91" },
  ];
  const tabs = [
    { key: "chat" as const, label: "Chat", icon: MessageCircle },
    { key: "memories" as const, label: "Memories", icon: Sparkles },
    { key: "history" as const, label: "Life", icon: Heart },
    { key: "mind" as const, label: "Mind", icon: Brain },
  ];
  function parentName(id: string) {
    return store.displayState?.inhabitants.find((inhabitant) => inhabitant.id === id)?.name ?? "A former inhabitant";
  }
  function toolLabel(name: string) {
    switch (name) {
      case "share_plan":
        return "Shared a plan";
      case "inspect":
        return "Examined something";
      case "recall":
        return "Searched a memory";
      case "read_document":
        return "Read a document";
      case "scratch":
        return "Tried a calculation";
      default:
        return name;
    }
  }
  function toolSummary(trace: ToolTrace) {
    if (trace.status === "pending") return "Starting action";
    if (trace.status === "running") return "Action in progress";
    if (trace.status === "completed") return trace.tool === "walk" ? "Arrived at the destination" : "Action completed";
    if (trace.status === "cancelled") return "Action cancelled";

    if (trace.arguments.query) return `Looking for “${trace.arguments.query}”`;

    if (trace.arguments.objectId) {
      const entity = store.displayState?.entities.find((entity) => entity.id === trace.arguments.objectId);

      return entity?.name ?? "An object nearby";
    }

    return "See the tool result";
  }

  async function load() {
    if (!store.world || !agent.value || loading.value || disposed) return;

    const current = generation;
    loading.value = true;

    try {
      const result = await worldsApi.profile(store.world.id, agent.value.id, store.replayTick);

      if (!disposed && current === generation) {
        profile.value = result;
        error.value = "";
      }
    } catch (failure) {
      if (!disposed && current === generation)
        error.value = getFirstApiErrorMessage(failure, "Their story could not be loaded. Trying again…");
    } finally {
      loading.value = false;
    }
  }
  const polling = usePolling(load, () => disposed, 1500, { immediate: false });
  watch(liveUpdates, (enabled) => {
    if (enabled) {
      polling.startPolling();
      void load();
    } else {
      generation++;
      polling.stopPolling();
    }
  });
  watch(
    () => store.profileTab,
    () => {
      query.value = "";
      content.value?.scrollTo(0, 0);
    }
  );
  watch(
    [() => store.world?.id, () => store.selectedId],
    () => {
      generation++;
      profile.value = null;
      error.value = "";
      void load();
    },
    { immediate: true }
  );
  watch(
    () => store.replayTick,
    () => {
      clearTimeout(seekTimer);
      seekTimer = setTimeout(load, 200);
    }
  );
  onBeforeUnmount(() => {
    disposed = true;
    generation++;
    clearTimeout(seekTimer);
  });
</script>
