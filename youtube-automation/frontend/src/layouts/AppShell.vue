<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'

const mobileMenuOpen = ref(false)

const closeMobileMenu = () => {
  mobileMenuOpen.value = false
}
</script>

<template>
  <div class="min-h-screen bg-canvas">
    <button
      v-if="mobileMenuOpen"
      type="button"
      class="fixed inset-0 z-30 bg-slate-950/50 lg:hidden"
      aria-label="Fechar menu"
      @click="closeMobileMenu"
    />

    <aside
      class="fixed inset-y-0 left-0 z-40 flex w-72 -translate-x-full flex-col bg-ink px-5 py-6 text-white transition-transform lg:translate-x-0"
      :class="{ 'translate-x-0': mobileMenuOpen }"
    >
      <div class="flex items-center gap-3 px-2">
        <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500 font-black">
          Y
        </div>
        <div>
          <p class="text-sm font-bold tracking-wide">YouTube</p>
          <p class="text-xs text-slate-400">Automation Studio</p>
        </div>
      </div>

      <nav class="mt-12 space-y-2" aria-label="Navegação principal">
        <RouterLink
          to="/"
          class="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-slate-300 transition hover:bg-white/10 hover:text-white [&.router-link-exact-active]:bg-brand-500 [&.router-link-exact-active]:text-white"
          @click="closeMobileMenu"
        >
          <span aria-hidden="true">⌂</span>
          Dashboard
        </RouterLink>
        <RouterLink
          to="/settings"
          class="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-slate-300 transition hover:bg-white/10 hover:text-white [&.router-link-exact-active]:bg-brand-500 [&.router-link-exact-active]:text-white"
          @click="closeMobileMenu"
        >
          <span aria-hidden="true">⚙</span>
          Configurações
        </RouterLink>
      </nav>

      <div class="mt-auto rounded-2xl border border-white/10 bg-white/5 p-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-slate-400">Próximo passo</p>
        <p class="mt-2 text-sm leading-6 text-slate-200">
          Crie seu primeiro job quando a API de processamento estiver disponível.
        </p>
      </div>
    </aside>

    <div class="lg:pl-72">
      <header
        class="sticky top-0 z-20 border-b border-slate-200/80 bg-canvas/90 px-4 py-4 backdrop-blur md:px-8"
      >
        <div class="flex items-center justify-between gap-4">
          <button
            type="button"
            class="rounded-lg border border-slate-200 bg-white px-3 py-2 text-slate-600 lg:hidden"
            aria-label="Abrir menu"
            @click="mobileMenuOpen = true"
          >
            ☰
          </button>
          <div class="hidden md:block">
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-brand-600">
              Creator studio
            </p>
            <p class="text-sm text-slate-500">Automação inteligente para seu canal</p>
          </div>
          <div class="ml-auto flex items-center gap-3">
            <span class="hidden text-sm font-medium text-slate-500 sm:inline">Ambiente local</span>
            <span class="h-2.5 w-2.5 rounded-full bg-emerald-500" aria-label="Ambiente ativo" />
          </div>
        </div>
      </header>

      <main class="mx-auto max-w-7xl px-4 py-8 md:px-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>
