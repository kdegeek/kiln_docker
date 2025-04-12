<script lang="ts">
  import FormElement from "$lib/utils/form_element.svelte"
  import { current_task_prompts } from "$lib/stores"
  import type { PromptResponse } from "$lib/types"
  import Warning from "$lib/ui/warning.svelte"

  export let prompt_method: string
  export let linked_model_selection: string | undefined = undefined

  export let exclude_cot = false
  export let custom_prompt_name: string | undefined = undefined
  export let fine_tune_prompt_id: string | undefined = undefined
  export let description: string | undefined = undefined
  export let info_description: string | undefined = undefined

  $: options = build_prompt_options(
    $current_task_prompts,
    exclude_cot,
    custom_prompt_name,
    fine_tune_prompt_id,
  )

  // Add this variable to track scrollability
  let isMenuScrollable = false
  let menuElement: HTMLElement

  // Function to check if menu is scrollable
  function checkIfScrollable() {
    if (menuElement) {
      isMenuScrollable = menuElement.scrollHeight > menuElement.clientHeight
    }
  }

  // Create an action to bind to the menu element
  function scrollableCheck(node: HTMLElement) {
    menuElement = node
    checkIfScrollable()

    // Create a mutation observer to detect content changes
    const observer = new MutationObserver(checkIfScrollable)
    observer.observe(node, { childList: true, subtree: true })

    return {
      destroy() {
        observer.disconnect()
      },
    }
  }

  // Watch for changes to options and recheck scrollability
  $: options, setTimeout(checkIfScrollable, 0)

  function build_prompt_options(
    current_task_prompts: PromptResponse | null,
    exclude_cot: boolean,
    custom_prompt_name: string | undefined,
    fine_tune_prompt_id: string | undefined,
  ): [string, [string, string][]][] {
    if (!current_task_prompts) {
      return [["Loading...", []]]
    }

    const grouped_options: [string, [string, string][]][] = []

    const generators: [string, string][] = []
    for (const generator of current_task_prompts.generators) {
      if (generator.chain_of_thought && exclude_cot) {
        continue
      }
      generators.push([generator.id, generator.name])
    }
    if (generators.length > 0) {
      grouped_options.push(["Prompt Generators", generators])
    }

    if (fine_tune_prompt_id) {
      grouped_options.push([
        "Fine-Tune Prompt",
        [[fine_tune_prompt_id, "Fine-Tune Specific Prompt"]],
      ])
    }

    if (custom_prompt_name) {
      grouped_options.push(["Custom Prompt", [["custom", custom_prompt_name]]])
    }

    const static_prompts: [string, string][] = []
    for (const prompt of current_task_prompts.prompts) {
      if (!prompt.id) {
        continue
      }
      if (prompt.chain_of_thought_instructions && exclude_cot) {
        continue
      }
      static_prompts.push([prompt.id, prompt.name])
    }
    if (static_prompts.length > 0) {
      grouped_options.push(["Saved Prompts", static_prompts])
    }
    return grouped_options
  }

  // Finetunes are tuned with specific prompts.
  $: is_fine_tune_model =
    linked_model_selection &&
    linked_model_selection.startsWith("kiln_fine_tune/")
  $: {
    update_fine_tune_prompt_selection(linked_model_selection)
  }
  function update_fine_tune_prompt_selection(model_id: string | undefined) {
    if (model_id && model_id.startsWith("kiln_fine_tune/")) {
      // Select the fine-tune prompt automatically, when selecting a fine-tuned model
      const fine_tune_id = model_id.substring("kiln_fine_tune/".length)
      fine_tune_prompt_id = "fine_tune_prompt::" + fine_tune_id
      prompt_method = fine_tune_prompt_id
    } else {
      fine_tune_prompt_id = undefined
      if (prompt_method.startsWith("fine_tune_prompt::")) {
        // Reset to basic, since fine-tune prompt is no longer available
        prompt_method = "simple_prompt_builder"
      }
    }
    // This shouldn't be needed, but it is. Svelte doesn't re-evaluate the options when the fine-tune prompt id changes.
    options = build_prompt_options(
      $current_task_prompts,
      exclude_cot,
      custom_prompt_name,
      fine_tune_prompt_id,
    )
  }
</script>

<FormElement
  label="Prompt Method"
  inputType="select"
  {description}
  {info_description}
  bind:value={prompt_method}
  id="prompt_method"
  bind:select_options_grouped={options}
/>

<div class="dropdown w-full relative">
  <div
    tabindex="0"
    role="button"
    class="select select-bordered w-full flex items-center"
  >
    <span class="truncate">
      {(() => {
        const flatOptions = options.flatMap((group) => group[1])
        const selectedOption = flatOptions.find(
          (item) => item[0] === prompt_method,
        )
        return selectedOption ? selectedOption[1] : ""
      })()}
    </span>
  </div>

  <!--svelte-ignore a11y-no-noninteractive-tabindex -->
  <div
    tabindex="0"
    class="dropdown-content relative bg-base-100 rounded-box z-[1] w-full p-2 shadow absolute max-h-[50vh] flex flex-col relative"
    style="bottom: auto; top: 100%; max-height: min(50vh, calc(100vh - var(--dropdown-top, 0px) - 20px));"
  >
    <ul
      class="menu overflow-y-auto overflow-x-hidden flex-nowrap"
      use:scrollableCheck
    >
      {#each options as option}
        <li class="menu-title">{option[0]}</li>
        {#each option[1] as item}
          <li>
            <button on:click={() => (prompt_method = item[0])}>{item[1]}</button
            >
          </li>
        {/each}
      {/each}
    </ul>

    <!-- Scroll indicator - only show if scrollable -->
    {#if isMenuScrollable}
      <div class="h-6">&nbsp;</div>
      <div
        class="absolute bottom-0 left-0 right-0 pointer-events-none rounded-b-md"
      >
        <div class="bg-white mx-3 w-full flex justify-center items-center py-1">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="opacity-60"
          >
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
    {/if}
  </div>
</div>

{#if is_fine_tune_model && prompt_method != fine_tune_prompt_id}
  <Warning
    warning_message="We strongly recommend using prompt the model was trained on when running a fine-tuned model."
  />
{/if}
