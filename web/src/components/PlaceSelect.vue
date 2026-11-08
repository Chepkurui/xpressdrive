<script setup>
import { usePlaces } from '@/composables/places'

defineProps({
  modelValue: { type: String, default: '' },
  id: String,
  required: Boolean,
  borders: { type: Boolean, default: true },
  placeholder: { type: String, default: 'Choose a town' },
})
defineEmits(['update:modelValue'])
const { grouped } = usePlaces()
</script>

<template>
  <select :id="id" :value="modelValue" :required="required" @change="$emit('update:modelValue', $event.target.value)">
    <option value="">{{ placeholder }}</option>
    <template v-for="[group, items] in grouped" :key="group">
      <optgroup v-if="borders || group !== 'Border posts'" :label="group">
        <option v-for="p in items" :key="p.code" :value="p.code">{{ p.name }}</option>
      </optgroup>
    </template>
  </select>
</template>
