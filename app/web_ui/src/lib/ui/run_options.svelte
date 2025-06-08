<script lang="ts">
  import FormElement from "$lib/utils/form_element.svelte"

  // These defaults are used by every provider I checked (OpenRouter, Fireworks, Together, etc)
  export let temperature: number = 1.0
  export let top_p: number = 1.0

  export let validate_temperature: (value: unknown) => string | null = (
    value: unknown,
  ) => {
    return validator(value, 0, 2, "Temperature")
  }

  export let validate_top_p: (value: unknown) => string | null = (
    value: unknown,
  ) => {
    return validator(value, 0, 1, "Top P")
  }

  export let validator: (
    value: unknown,
    min: number,
    max: number,
    name: string,
  ) => string | null = (
    value: unknown,
    min: number,
    max: number,
    name: string,
  ) => {
    // Handle string values by attempting conversion
    let numValue: number

    if (typeof value === "string") {
      if (value.trim() === "") {
        return "Value is required"
      }
      numValue = parseFloat(value)
      if (isNaN(numValue)) {
        return "Please enter a valid number"
      }
    } else if (typeof value === "number") {
      numValue = value
    } else {
      return "Please enter a valid number"
    }

    if (numValue < min) {
      return `${name} must be at least ${min}`
    }
    if (numValue > max) {
      return `${name} must be at most ${max}`
    }

    return null
  }
</script>

<FormElement
  id="temperature"
  label="Temperature"
  inputType="input"
  info_description="A value from 0.0 to 2.0. Temperature is a parameter that controls the randomness of the model's output. Lower values make the output more focused and deterministic, while higher values make it more creative and varied."
  bind:value={temperature}
  validator={validate_temperature}
/>

<FormElement
  id="top_p"
  label="Top P"
  inputType="input"
  info_description="A value from 0.0 to 1.0. Top P is a parameter that controls the diversity of the model's output. Lower values make the output more focused and deterministic, while higher values make it more creative and varied."
  bind:value={top_p}
  validator={validate_top_p}
/>
