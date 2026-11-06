<script setup lang="ts">
import { onMounted } from 'vue'

import { useSystemStore } from '../stores/system'

const systemStore = useSystemStore()

onMounted(() => {
  void systemStore.checkHealth()
})
</script>

<template>
  <section class="space-y-8">
    <div class="flex flex-col justify-between gap-4 md:flex-row md:items-end">
      <div>
        <p class="text-sm font-semibold text-brand-600">Visão geral</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight text-slate-950 md:text-4xl">
          Seu estúdio em um só lugar
        </h1>
        <p class="mt-3 max-w-2xl text-slate-500">
          Acompanhe a saúde da automação e prepare o conteúdo do seu próximo vídeo.
        </p>
      </div>
      <RouterLink
        to="/settings"
        class="inline-flex items-center justify-center rounded-xl bg-brand-600 px-4 py-3 text-sm font-bold text-white shadow-lg shadow-brand-500/20 transition hover:bg-brand-500"
      >
        Ajustar configurações
      </RouterLink>
    </div>

    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <article
        v-for="card in [
          'Vídeos processados',
          'Jobs ativos',
          'Contas conectadas',
          'Taxa de sucesso',
        ]"
        :key="card"
        class="rounded-2xl border border-slate-200 bg-white p-5 shadow-card"
      >
        <p class="text-sm font-medium text-slate-500">{{ card }}</p>
        <p class="mt-5 text-3xl font-black text-slate-300">—</p>
        <p class="mt-2 text-xs text-slate-400">Disponível nas próximas integrações</p>
      </article>
    </div>

    <article class="rounded-3xl border border-slate-200 bg-white p-6 shadow-card md:p-8">
      <div class="flex flex-col justify-between gap-5 sm:flex-row sm:items-start">
        <div>
          <p class="text-sm font-semibold text-brand-600">Status do sistema</p>
          <h2 class="mt-2 text-2xl font-black text-slate-950">Backend e serviços locais</h2>
        </div>
        <span
          class="inline-flex w-fit items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold"
          :class="
            systemStore.isHealthy ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
          "
        >
          <span class="h-2 w-2 rounded-full bg-current" />
          {{ systemStore.isHealthy ? 'Operacional' : 'Verificar conexão' }}
        </span>
      </div>

      <div class="mt-8 rounded-2xl bg-slate-50 p-5">
        <p v-if="systemStore.loading" class="text-sm text-slate-500">Verificando o backend...</p>
        <div
          v-else-if="systemStore.error"
          class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <p class="text-sm text-rose-700">{{ systemStore.error }}</p>
          <button
            type="button"
            class="rounded-lg bg-white px-3 py-2 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-100"
            @click="systemStore.checkHealth"
          >
            Tentar novamente
          </button>
        </div>
        <p v-else class="text-sm text-slate-600">
          API FastAPI respondendo com status
          <strong class="text-emerald-700">{{ systemStore.status }}</strong
          >.
        </p>
      </div>
    </article>
  </section>
</template>
