<script setup lang="ts">
import { onMounted } from 'vue'

import { useSettingsStore } from '../stores/settings'

const settingsStore = useSettingsStore()

onMounted(() => {
  void settingsStore.load()
})
</script>

<template>
  <section class="space-y-8">
    <div>
      <p class="text-sm font-semibold text-brand-600">Configurações</p>
      <h1 class="mt-2 text-3xl font-black tracking-tight text-slate-950">Ajuste seu ambiente</h1>
      <p class="mt-3 max-w-2xl text-slate-500">
        Consulte as configurações públicas usadas pelo pipeline de automação.
      </p>
    </div>

    <article class="rounded-3xl border border-slate-200 bg-white p-6 shadow-card md:p-8">
      <div v-if="settingsStore.loading" class="py-12 text-center text-sm text-slate-500">
        Carregando configurações...
      </div>
      <div v-else-if="settingsStore.error" class="space-y-4 py-8">
        <p class="text-sm text-rose-700">{{ settingsStore.error }}</p>
        <button
          type="button"
          class="rounded-xl bg-brand-600 px-4 py-3 text-sm font-bold text-white"
          @click="settingsStore.load"
        >
          Tentar novamente
        </button>
      </div>
      <form v-else class="space-y-6" @submit.prevent="settingsStore.save">
        <div class="grid gap-5 md:grid-cols-2">
          <label v-for="field in settingsStore.editableFields" :key="field.key" class="space-y-2">
            <span class="text-sm font-bold text-slate-700">{{ field.label }}</span>
            <input
              v-model="settingsStore.form[field.key]"
              :type="field.type"
              class="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:bg-white"
            />
          </label>
        </div>
        <label class="block max-w-xl space-y-2">
          <span class="text-sm font-bold text-slate-700">Chave administrativa</span>
          <input
            v-model="settingsStore.adminKey"
            type="password"
            autocomplete="off"
            class="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-brand-500 focus:bg-white"
            placeholder="Usada somente nesta solicitação"
          />
          <span class="block text-xs text-slate-400">
            A chave não é salva no navegador e é enviada apenas ao atualizar configurações.
          </span>
        </label>
        <div
          class="flex flex-col justify-between gap-4 border-t border-slate-100 pt-6 sm:flex-row sm:items-center"
        >
          <p v-if="settingsStore.message" class="text-sm text-emerald-700">
            {{ settingsStore.message }}
          </p>
          <p v-else class="text-sm text-slate-400">
            Alterações administrativas exigem a chave configurada na API.
          </p>
          <button
            type="submit"
            :disabled="settingsStore.saving"
            class="rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-brand-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {{ settingsStore.saving ? 'Salvando...' : 'Salvar alterações' }}
          </button>
        </div>
      </form>
    </article>
  </section>
</template>
