<script lang="ts">
  import { onMount } from "svelte"
  import { client } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import type { FinetuneDatasetInfo } from "$lib/types"
  import OptionList from "$lib/ui/option_list.svelte"
  import { formatDate } from "$lib/utils/formatters"
  import Dialog from "$lib/ui/dialog.svelte"
  import FormContainer from "$lib/utils/form_container.svelte"
  import FormElement from "$lib/utils/form_element.svelte"
  import { goto } from "$app/navigation"
  import type { DatasetSplit } from "$lib/types"

  let finetune_dataset_info: FinetuneDatasetInfo | null = null
  let loading = true
  let error: KilnError | null = null

  export let project_id: string
  export let task_id: string
  export let selected_dataset: DatasetSplit | null = null

  let create_dataset_dialog: Dialog | null = null

  onMount(async () => {
    load_finetune_dataset_info()
  })

  async function load_finetune_dataset_info() {
    try {
      loading = true
      error = null
      if (!project_id || !task_id) {
        throw new Error("Project or task ID not set.")
      }
      const { data: finetune_dataset_info_response, error: get_error } =
        await client.GET(
          "/api/projects/{project_id}/tasks/{task_id}/finetune_dataset_info",
          {
            params: {
              path: {
                project_id,
                task_id,
              },
            },
          },
        )
      if (get_error) {
        throw get_error
      }
      if (!finetune_dataset_info_response) {
        throw new Error("Invalid response from server")
      }
      finetune_dataset_info = finetune_dataset_info_response
    } catch (e) {
      if (e instanceof Error && e.message.includes("Load failed")) {
        error = new KilnError("Could not load fine-tune dataset info.", null)
      } else {
        error = createKilnError(e)
      }
    } finally {
      loading = false
    }
  }

  $: tag_select_options = [
    {
      label: "Dataset Tags",
      options:
        finetune_dataset_info?.funetune_tags?.map((tag) => ({
          label: tag.tag,
          value: tag.tag,
          description: `The tag '${tag.tag}' has ${tag.count} samples.`,
        })) || [],
    },
  ]

  $: top_options = [
    ...(finetune_dataset_info?.existing_finetunes.length
      ? [
          {
            id: "existing_dataset",
            name: "Use Training Dataset from Existing Fine-Tune",
            description:
              "When comparing multiple models, it's best to used exactly the same training dataset.",
          },
        ]
      : []),
    ...(finetune_dataset_info?.funetune_tags.length
      ? [
          {
            id: "new_dataset",
            name: "New Training Dataset",
            description: "Create a training set using your current data.",
          },
        ]
      : []),
    {
      id: "add",
      name: "Add Training Data",
      description:
        "Add a new training data using synthetic data generation, CSV upload, or by tagging existing data.",
    },
  ]

  let select_existing_dataset = false
  function select_top_option(option: string) {
    select_existing_dataset = false
    if (option === "new_dataset") {
      if (finetune_dataset_info?.funetune_tags.length === 1) {
        dataset_tag = finetune_dataset_info?.funetune_tags[0].tag
      }
      create_dataset_dialog?.show()
    } else if (option === "add") {
      show_add_data()
    } else if (option === "existing_dataset") {
      select_existing_dataset = true
    }
  }

  function edit_dataset() {
    selected_dataset = null
    select_existing_dataset = false
  }

  let new_dataset_split = "train_val"
  let dataset_tag: string | null = null
  $: selected_dataset_tag_data = finetune_dataset_info?.funetune_tags.find(
    (t) => t.tag === dataset_tag,
  )
  let create_dataset_split_error: KilnError | null = null
  let create_dataset_split_loading = false
  async function create_dataset() {
    try {
      if (!dataset_tag) {
        throw new Error("No dataset tag selected")
      }
      create_dataset_split_loading = true
      create_dataset_split_error = null

      let dataset_filter_id = "custom_tag"
      if (dataset_filter_id === "custom_tag") {
        dataset_filter_id = "tag::" + dataset_tag
      }

      const { data: create_dataset_split_response, error: post_error } =
        await client.POST(
          "/api/projects/{project_id}/tasks/{task_id}/dataset_splits",
          {
            params: {
              path: {
                project_id,
                task_id,
              },
            },
            body: {
              // @ts-expect-error types are validated by the server
              dataset_split_type: new_dataset_split,
              filter_id: dataset_filter_id,
            },
          },
        )
      if (post_error) {
        throw post_error
      }
      if (!create_dataset_split_response || !create_dataset_split_response.id) {
        throw new Error("Invalid response from server")
      }
      selected_dataset = create_dataset_split_response
      create_dataset_dialog?.close()
    } catch (e) {
      if (e instanceof Error && e.message.includes("Load failed")) {
        create_dataset_split_error = new KilnError(
          "Could not create a dataset split for fine-tuning.",
          null,
        )
      } else {
        create_dataset_split_error = createKilnError(e)
      }
    } finally {
      create_dataset_split_loading = false
    }
  }

  function show_add_data() {
    let link = `/dataset/${project_id}/${task_id}/add_data?reason=fine_tune&splits=fine_tune_data:1.0&finetune_link=${encodeURIComponent(
      `/fine_tune/${project_id}/${task_id}/create_finetune`,
    )}`
    goto(link)
  }
</script>

{#if loading}
  <div class="w-full flex justify-center items-center">
    <div class="loading loading-spinner loading-lg"></div>
  </div>
{:else if error}
  <div class="text-error text-sm">
    {error.getMessage() || "An unknown error occurred"}
  </div>
{:else if finetune_dataset_info}
  <div>
    {#if selected_dataset}
      <div class="flex flex-row gap-x-2">
        <div
          class="text-sm input input-bordered flex place-items-center w-full"
        >
          <div>
            Dataset '{selected_dataset.name}' created
            {formatDate(selected_dataset.created_at)}
          </div>
        </div>
        <button class="btn btn-sm btn-md" on:click={edit_dataset}
          >Change Dataset</button
        >
      </div>
    {:else if !select_existing_dataset}
      <OptionList options={top_options} select_option={select_top_option} />
    {:else if select_existing_dataset}
      <div class="text font-medium mb-4">
        Use Training Dataset from Existing Fine-Tune
        {#if top_options.length > 1}
          <span class="text-sm text-gray-500 font-normal">
            <button
              class="link"
              on:click={() => {
                select_existing_dataset = false
              }}
            >
              or select another option
            </button>
          </span>
        {/if}
      </div>
      <div class="flex flex-col gap-4 text-sm max-w-[600px]">
        {#each finetune_dataset_info.existing_datasets as dataset}
          {@const finetunes = finetune_dataset_info.existing_finetunes.filter(
            (f) => f.dataset_split_id === dataset.id,
          )}
          {#if finetunes.length > 0 && dataset.id}
            <button
              class="card card-bordered border-base-300 bg-base-200 shadow-md w-full px-4 py-3 indicator grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 overflow-hidden text-left"
              on:click={() => {
                selected_dataset = dataset
              }}
            >
              <div class="text-xs text-gray-500">Dataset Name</div>
              <div class="text-medium">{dataset.name}</div>
              <div class="text-xs text-gray-500">Created</div>
              <div>{formatDate(dataset.created_at)}</div>
              {#each Object.keys(dataset.split_contents) as split_type}
                <div class="text-xs text-gray-500">
                  Split: {split_type}
                </div>
                <div>
                  {dataset.split_contents[split_type].length} items
                </div>
              {/each}
              <div class="text-xs text-gray-500">Tunes Using Dataset</div>
              <div>{finetunes.map((f) => f.name).join(", ")}</div>
            </button>
          {/if}
        {/each}
      </div>
    {/if}
  </div>
{/if}

<Dialog title="Create Training Dataset" bind:this={create_dataset_dialog}>
  <div class="font-light text-sm mb-6">
    <div class="font-light text-sm mb-6">
      Snapshot your current dataset for training, filtering to a specific tag.
    </div>
    <div class="flex flex-row gap-6 justify-center flex-col">
      <FormContainer
        submit_label="Create Dataset"
        on:submit={create_dataset}
        bind:error={create_dataset_split_error}
        bind:submitting={create_dataset_split_loading}
      >
        <div>
          <FormElement
            label="Filter to Tag"
            description="Samples with this tag will be included in the training dataset."
            info_description="Any tag starting with 'fine_tune' will be available here. Advanced users can create their own tags to manage multiple training datasets."
            inputType="fancy_select"
            optional={false}
            id="dataset_filter"
            fancy_select_options={tag_select_options || []}
            bind:value={dataset_tag}
          />
          {#if selected_dataset_tag_data && selected_dataset_tag_data.count < 25}
            <div class="text-error text-sm mt-1">
              The selected dataset tag has less than 25 samples. We suggest at
              least 25 samples for a good fine-tune.
            </div>
          {:else if selected_dataset_tag_data}
            <div class="text-sm mt-1">
              The selected dataset tag has {selected_dataset_tag_data.count}
              samples.
            </div>
          {/if}
        </div>

        <div class="collapse collapse-arrow bg-base-200">
          <input type="checkbox" class="peer" />
          <div class="collapse-title font-medium flex items-center">
            Advanced Options
          </div>
          <div class="collapse-content flex flex-col gap-4">
            <FormElement
              label="Dataset Splits"
              description="Select ratios for splitting the data into training, validation, and test."
              info_description="If in doubt, leave the the recommended value. If you're using an external test set such as Kiln Evals, you don't need a test set here."
              inputType="select"
              optional={false}
              id="dataset_split"
              select_options={[
                ["train_val", "80% Training, 20% Validation (Recommended)"],
                ["train_test", "80% Training, 10% Test, 10% Validation"],
                ["train_test_val", "60% Training, 20% Test, 20% Validation"],
                ["train_test_val_80", "80% Training, 10% Test, 10% Validation"],
                ["all", "100% Training"],
              ]}
              bind:value={new_dataset_split}
            />
          </div>
        </div>
      </FormContainer>
    </div>
  </div>
</Dialog>
