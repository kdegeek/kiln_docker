<script lang="ts">
  import AppPage from "../../../../app_page.svelte"
  import SelectEvalTemplate from "./select_eval_template.svelte"
  import type { EvalOutputScore } from "$lib/types"
  import type { EvalTemplateResult } from "./eval_template"
  import FormContainer from "$lib/utils/form_container.svelte"
  import type { Task } from "$lib/types"
  import FormElement from "$lib/utils/form_element.svelte"
  import FormList from "$lib/utils/form_list.svelte"
  import { load_task } from "$lib/stores"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { onMount } from "svelte"
  import { page } from "$app/stores"
  import Warning from "$lib/ui/warning.svelte"
  import { tick } from "svelte"

  // Loading
  let loading_task = true
  let loading_error: KilnError | undefined = undefined
  $: loading = loading_task
  let task: Task | null = null
  onMount(async () => {
    // Need to wait for the page params to be available
    await tick()
    try {
      task = await load_task($page.params.project_id, $page.params.task_id)
    } catch (e) {
      loading_error = createKilnError(e)
    } finally {
      loading_task = false
    }
  })

  let selected_template: string | undefined = undefined
  function on_selected_template(template: EvalTemplateResult) {
    // Populate out model from the template
    name = template.name
    description = template.description
    output_scores = template.output_scores
    selected_template = template.template_id
  }

  // Data for the creation
  let name: string = ""
  let description: string = ""
  let output_scores: EvalOutputScore[] = []

  // UI State
  let submit_visible: boolean = false
  let create_evaluator_error: KilnError | undefined = undefined
  let create_evaluator_loading: boolean = false

  function create_evaluator() {
    console.log("create_evaluator")
  }
</script>

<div class="max-w-[1400px]">
  <AppPage
    title="Create a New Evaluator"
    subtitle="Evaluators judge performance, and help compare different methods of running your task."
  >
    {#if loading}
      <div class="w-full min-h-[50vh] flex justify-center items-center">
        <div class="loading loading-spinner loading-lg"></div>
      </div>
    {:else if loading_error}
      <div
        class="w-full min-h-[50vh] flex flex-col justify-center items-center gap-2"
      >
        <div class="font-medium">Error Loading Task Information</div>
        <div class="text-error text-sm">
          {loading_error?.getMessage() || "An unknown error occurred"}
        </div>
      </div>
    {:else if !selected_template}
      <SelectEvalTemplate
        selected_template_callback={on_selected_template}
        bind:task
      />
    {:else}
      <FormContainer
        {submit_visible}
        submit_label="Create Evaluator"
        on:submit={create_evaluator}
        bind:error={create_evaluator_error}
        bind:submitting={create_evaluator_loading}
      >
        <div class="text-xl font-bold">Part 1: Evaluator Details</div>
        <FormElement
          label="Evaluator Name"
          description="Give your evaluator a name that will help you identify it later."
          inputType="input"
          id="name"
          bind:value={name}
        />
        <FormElement
          label="Evaluator Description"
          description="Give your evaluator a description."
          inputType="textarea"
          id="description"
          bind:value={description}
        />

        <div class="text-sm font-medium text-left pt-6 flex flex-col gap-1">
          <div class="text-xl font-bold" id="requirements_part">
            Part 2: Evaluator Output Scores
          </div>
          <div class="text-xs text-gray-500">
            Define the scores that the evaluator will output.
          </div>
          {#if selected_template !== "custom"}
            <Warning
              warning_message="Since you selected a template, you can't edit these. Use the 'Custom' template to create your own scores."
              warning_color="warning"
              tight={true}
            />
          {/if}
        </div>

        <FormList
          bind:content={output_scores}
          content_label="Output Score"
          let:item_index
          frozen={selected_template !== "custom"}
        >
          <div class="flex flex-col gap-3">
            <div class="flex flex-row gap-1">
              <div class="grow flex flex-col gap-1">
                <FormElement
                  label="Score Name"
                  id="score_name_{item_index}"
                  light_label={true}
                  bind:value={output_scores[item_index].name}
                  max_length={32}
                  disabled={selected_template !== "custom"}
                />
              </div>
              <div class="flex flex-col gap-1">
                <FormElement
                  label="Rating Type"
                  inputType="select"
                  id="score_type_{item_index}"
                  light_label={true}
                  select_options={[
                    ["five_star", "5 Star"],
                    ["pass_fail", "Pass / Fail"],
                    ["pass_fail_critical", "Pass / Fail / Critical"],
                  ]}
                  bind:value={output_scores[item_index].type}
                  disabled={selected_template !== "custom"}
                />
              </div>
            </div>
            <div class="grow flex flex-col gap-1">
              <FormElement
                label="Instructions"
                inputType="textarea"
                id="score_instructions_{item_index}"
                light_label={true}
                bind:value={output_scores[item_index].instruction}
                disabled={selected_template !== "custom"}
              />
            </div>
          </div>
        </FormList>

        <div class="text-sm font-medium text-left pt-6 flex flex-col gap-1">
          <div class="text-xl font-bold" id="requirements_part">
            Part 3: Evaluation Datasets
          </div>
          <div class="text-xs text-gray-500">
            Specify which which parts of your dataset this evaluator should run
            on.
          </div>
        </div>
      </FormContainer>
    {/if}
  </AppPage>
</div>
