<script lang="ts">
  import {
    available_models,
    load_available_models,
    available_model_details,
    ui_state,
  } from "$lib/stores"
  import type { AvailableModels } from "$lib/types"
  import { onMount } from "svelte"
  import { get } from "svelte/store"
  import FormElement from "$lib/utils/form_element.svelte"
  import Warning from "$lib/ui/warning.svelte"

  const UNTESTED_WARNING =
    "This model has not been tested with Kiln. It may not work as expected."
  const DATA_GEN_WARNING =
    "This model is not recommended for use with data generation. It's known to generate incorrect data."
  const LOGPROBS_WARNING =
    "This model does not support logprobs. It will likely fail when running a G-eval or other logprob queries."
  const STRUCTURED_WARNING =
    "This model is not recommended for use with tasks requiring structured output. It fails to consistently return structured data."
  const DATA_GEN_SUGGESTION =
    "For data gen we suggest using a high quality model such as GPT 4.1, Sonnet, Gemini Pro or R1."
  const EVALS_SUGGESTION =
    "For evals we suggest using a high quality model such as GPT 4.1, Sonnet, Gemini Pro or R1."

  export let model: string = $ui_state.selected_model
  export let requires_structured_output: boolean = false
  export let requires_data_gen: boolean = false
  export let requires_logprobs: boolean = false
  export let error_message: string | null = null
  export let suggested_mode: "data_gen" | "evals" | null = null
  $: $ui_state.selected_model = model
  $: model_options = format_model_options(
    $available_models || {},
    requires_structured_output,
    requires_data_gen,
    requires_logprobs,
    $ui_state.current_task_id,
  )

  // Export the parsed model name and provider name
  export let model_name: string | null = null
  export let provider_name: string | null = null
  $: get_model_provider(model)
  function get_model_provider(model_provider: string) {
    model_name = model_provider
      ? model_provider.split("/").slice(1).join("/")
      : null
    provider_name = model_provider ? model_provider.split("/")[0] : null
  }

  onMount(async () => {
    await load_available_models()
  })

  let unsupported_models: [string, string][] = []
  let untested_models: [string, string][] = []
  let previous_model: string = model

  function get_model_warning(selected: string): string | null {
    if (untested_models.find((m) => m[0] === selected)) {
      return UNTESTED_WARNING
    }
    if (unsupported_models.find((m) => m[0] === selected)) {
      if (requires_data_gen) {
        return DATA_GEN_WARNING
      }
      if (requires_logprobs) {
        return LOGPROBS_WARNING
      }
      if (requires_structured_output) {
        return STRUCTURED_WARNING
      }
    }

    const [provider_id, ...model_parts] = selected.split("/")
    const model_id = model_parts.join("/")
    const details = available_model_details(
      model_id,
      provider_id,
      get(available_models),
    )

    if (suggested_mode === "data_gen" && !details?.suggested_for_data_gen) {
      return DATA_GEN_SUGGESTION
    }

    if (suggested_mode === "evals" && !details?.suggested_for_evals) {
      return EVALS_SUGGESTION
    }

    return null
  }

  function confirm_model_select(event: Event) {
    const select = event.target as HTMLSelectElement
    const selected = select.value
    const warning = get_model_warning(selected)
    if (warning && !confirm(warning)) {
      select.value = previous_model
      model = previous_model
      return
    }
    previous_model = selected
  }
  function format_model_options(
    providers: AvailableModels[],
    structured_output: boolean,
    requires_data_gen: boolean,
    requires_logprobs: boolean,
    current_task_id: string | null,
  ): [string, [unknown, string][]][] {
    let options = []
    unsupported_models = []
    untested_models = []
    for (const provider of providers) {
      let model_list = []
      for (const model of provider.models) {
        // Exclude models that are not available for the current task
        if (
          model &&
          model.task_filter &&
          current_task_id &&
          !model.task_filter.includes(current_task_id)
        ) {
          continue
        }

        let id = provider.provider_id + "/" + model.id
        let long_label = provider.provider_name + " / " + model.name
        if (model.untested_model) {
          untested_models.push([id, long_label])
          continue
        }
        if (requires_data_gen && !model.supports_data_gen) {
          unsupported_models.push([id, long_label])
          continue
        }
        if (structured_output && !model.supports_structured_output) {
          unsupported_models.push([id, long_label])
          continue
        }
        if (requires_logprobs && !model.supports_logprobs) {
          unsupported_models.push([id, long_label])
          continue
        }
        let model_name = model.name
        if (suggested_mode === "data_gen" && model.suggested_for_data_gen) {
          model_name = model.name + "  —  Recommended"
        } else if (suggested_mode === "evals" && model.suggested_for_evals) {
          model_name = model.name + "  —  Recommended"
        }
        model_list.push([id, model_name])
      }
      if (model_list.length > 0) {
        options.push([provider.provider_name, model_list])
      }
    }

    if (untested_models.length > 0) {
      options.push(["Untested Models", untested_models])
    }

    if (unsupported_models.length > 0) {
      let not_recommended_label = "Not Recommended"
      if (requires_data_gen) {
        not_recommended_label = "Not Recommended - Data Gen Not Supported"
      } else if (requires_structured_output) {
        not_recommended_label = "Not Recommended - Structured Output Fails"
      } else if (requires_logprobs) {
        not_recommended_label = "Not Recommended - Logprobs Not Supported"
      }
      options.push([not_recommended_label, unsupported_models])
    }

    // @ts-expect-error this is the correct format, but TS isn't finding it
    return options
  }

  // Extra check to make sure the model is available to use
  export function get_selected_model(): string | null {
    for (const provider of model_options) {
      if (provider[1].find((m) => m[0] === model)) {
        return model
      }
    }
    return null
  }

  $: selected_model_untested = untested_models.find((m) => m[0] === model)
  $: selected_model_unsupported = unsupported_models.find((m) => m[0] === model)

  $: selected_model_suggested_data_gen =
    available_model_details(model_name, provider_name, $available_models)
      ?.suggested_for_data_gen || false

  $: selected_model_suggested_evals =
    available_model_details(model_name, provider_name, $available_models)
      ?.suggested_for_evals || false
</script>

<div>
  <FormElement
    label="Model"
    bind:value={model}
    id="model"
    inputType="select"
    on_select={confirm_model_select}
    bind:error_message
    select_options_grouped={model_options}
  />

  {#if selected_model_untested}
    <Warning large_icon warning_message={UNTESTED_WARNING} />
  {:else if selected_model_unsupported}
    {#if requires_data_gen}
      <Warning large_icon warning_message={DATA_GEN_WARNING} />
    {:else if requires_logprobs}
      <Warning large_icon warning_message={LOGPROBS_WARNING} />
    {:else if requires_structured_output}
      <Warning large_icon warning_message={STRUCTURED_WARNING} />
    {/if}
  {:else if suggested_mode === "data_gen"}
    <Warning
      warning_icon={!model
        ? "info"
        : selected_model_suggested_data_gen
          ? "check"
          : "exclaim"}
      warning_color={!model
        ? "gray"
        : selected_model_suggested_data_gen
          ? "success"
          : "warning"}
      warning_message={DATA_GEN_SUGGESTION}
    />
  {:else if suggested_mode === "evals"}
    <Warning
      warning_icon={!model
        ? "info"
        : selected_model_suggested_evals
          ? "check"
          : "exclaim"}
      warning_color={!model
        ? "gray"
        : selected_model_suggested_evals
          ? "success"
          : "warning"}
      warning_message={EVALS_SUGGESTION}
    />
  {/if}
</div>
