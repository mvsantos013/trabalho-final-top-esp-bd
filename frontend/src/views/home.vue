<template>
  <div>
    <h1 class="text-center tracking-widest text-lg my-10">
      Detector de Phishing
    </h1>

    <div class="max-w-lg mx-auto bg-white p-5 shadow-xl rounded-md">
      <q-form @submit.prevent="onSubmit" autofocus>
        <q-input
          v-model="url"
          placeholder="URL"
          :disable="validating"
        ></q-input>

        <div class="text-right mt-10">
          <q-btn type="submit" color="primary" :loading="validating">
            Verificar
          </q-btn>
        </div>
      </q-form>
    </div>

    <div
      v-if="result"
      class="max-w-3xl mx-auto bg-white mt-16 px-5 shadow-xl rounded-md"
    >
      <h2 class="tracking-widest">Validation Result</h2>

      <div>
        O site alvo é <b>{{ result.result ? 'verdadeiro' : 'phishing' }}</b
        >.
      </div>

      <div class="py-2">
        <div class="mb-3">
          <h3 class="leading-loose font-semibold">URL</h3>
          <div>{{ result.url }}</div>
        </div>

        <div class="mb-3">
          <h3 class="leading-loose font-semibold">Metadata</h3>
          <div v-for="(value, key) in result.metadata" :key="key">
            <li>
              <span class="text-gray-500">{{ key }}</span
              >: "{{ value }}"
            </li>
          </div>
        </div>

        <div class="mb-3">
          <h3 class="leading-loose font-semibold">
            Top Resultados da busca no DuckDuckGo
          </h3>
          <div v-for="(value, index) in result.search_result" :key="index">
            <li>
              {{ value }}
            </li>
          </div>
        </div>

        <div class="mb-3">
          <h3 class="leading-loose font-semibold">RDF (TURTLE)</h3>
          <pre>{{ result.rdf }}</pre>
        </div>

        <div class="mb-3">
          <h3 class="leading-loose font-semibold">RDFs isomórficos</h3>
          <pre>{{ result.result }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '@/utils/api'

export default {
  data() {
    return {
      url: null,
      result: null,
      validating: false,
      error: null,
    }
  },
  methods: {
    async onSubmit() {
      this.result = null
      this.error = null
      this.validating = true
      try {
        const response = await api.validateUrl(this.url)
        this.result = response.data
      } catch (e) {
        this.error = `Erro: ${e}`
      }
      this.validating = false
    },
  },
}
</script>
