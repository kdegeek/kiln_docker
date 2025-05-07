<script lang="ts">
  import AppPage from "../../app_page.svelte"
  import { page } from "$app/stores"
  import Dialog from "$lib/ui/dialog.svelte"
  import { ui_state } from "$lib/stores"

  const validReasons = ["generic", "eval", "fine_tune"] as const
  type Reason = (typeof validReasons)[number]

  let manual_dialog: Dialog | null = null

  $: dataset_link = `/dataset/${$ui_state.current_project_id}/${$ui_state.current_task_id}`
  $: reason = validReasons.includes(
    $page.url.searchParams.get("reason") as Reason,
  )
    ? ($page.url.searchParams.get("reason") as Reason)
    : "generic"

  $: title =
    reason === "generic"
      ? "Add Data"
      : reason === "eval"
        ? "Setup Data for your Eval"
        : "Setup Data for Fine-tuning"
  $: reason_name =
    reason === "generic" ? "dataset" : reason === "eval" ? "eval" : "fine tune"

  $: splits = (() => {
    const splitsParam = $page.url.searchParams.get("splits")
    if (!splitsParam) return {}

    try {
      const splitMap: Record<string, number> = {}
      const pairs = splitsParam.split(",")

      for (const pair of pairs) {
        const [name, value] = pair.split(":").map((s) => s.trim())
        const numValue = parseFloat(value)
        if (isNaN(numValue) || numValue < 0 || numValue > 1) {
          throw new Error("Invalid split value")
        }
        splitMap[name] = numValue
      }

      // Validate that splits sum to 1
      const total = Object.values(splitMap).reduce((sum, val) => sum + val, 0)
      if (Math.abs(total - 1) > 0.001) {
        throw new Error("Split values must sum to 1")
      }

      return splitMap
    } catch (e) {
      console.warn("Invalid splits parameter, using default", e)
      return {}
    }
  })()

  $: splitsArray = Object.entries(splits).map(([name, value]) => ({
    name,
    value,
  }))

  $: data_source_descriptions = [
    {
      id: "synthetic",
      name: "Synthetic Data",
      description: `Generate synthetic data for your ${reason_name} using our interactive tool.`,
      recommended: true,
      highlight_title: null,
    },
    {
      id: "csv",
      name: "Upload CSV",
      description: `Upload a CSV file to add data to your ${reason_name}.`,
      recommended: false,
      highlight_title: null,
    },
    ...(splitsArray.length > 0
      ? [
          {
            id: "manual",
            name: "Manually Tag Existing Data",
            description: `Tag data which is already in your dataset to be used for your ${reason_name}.`,
            recommended: false,
            highlight_title: null,
          },
        ]
      : []),
  ]

  function select_data_source(id: string) {
    if (id === "manual") {
      manual_dialog?.show()
      return
    }
  }
</script>

<AppPage {title} subtitle="Create data or add existing data">
  {#if splitsArray.length > 0}
    <div class="font-light">
      Data will be assigned to the following dataset tags:
      {#each splitsArray as split}
        <span class="mx-2">
          <span class="badge badge-outline mx-2">
            {split.name}: {Math.round(split.value * 100)}%
          </span>
        </span>
      {/each}
    </div>
  {/if}
  <div class="flex flex-col gap-6 pt-8 max-w-[500px]">
    <div class="text-xl font-bold pb-4 text-center">Select Data Source</div>
    {#each data_source_descriptions as data_source_description}
      <button
        class="cursor-pointer text-left"
        on:click={() => {
          select_data_source(data_source_description.id)
        }}
      >
        <div
          class="card card-bordered border-base-300 bg-base-200 shadow-md w-full p-6 indicator"
        >
          {#if data_source_description.recommended}
            <div class="indicator-item indicator-center badge badge-primary">
              Recommended
            </div>
          {:else if data_source_description.highlight_title}
            <div class="indicator-item indicator-center badge badge-secondary">
              {data_source_description.highlight_title}
            </div>
          {/if}
          <div class="flex flex-col">
            <div class="font-medium">
              {data_source_description.name}
            </div>
            <div class="font-light pt-2">
              {data_source_description.description}
            </div>
          </div>
        </div>
      </button>
    {/each}
  </div>
</AppPage>

<Dialog
  bind:this={manual_dialog}
  title="Manually Tag Existing Data"
  action_buttons={[
    {
      label: "Cancel",
      isCancel: true,
    },
    {
      label: "Open Dataset in New Tab",
      isPrimary: true,
      action: () => {
        window.open(dataset_link, "_blank")
        return false
      },
    },
  ]}
>
  <div class="font-light flex flex-col gap-4">
    <p>
      Follow these steps to manually tag existing data to be used for your {reason_name}.
    </p>
    {#if splitsArray.length > 0}
      <div role="alert" class="rounded-box bg-base-200 p-4">
        Be sure to assign the following tags in the requested proportions:
        {#each splitsArray as split}
          <span class="mx-2">
            <span class="badge badge-outline mx-2">
              {split.name}: {Math.round(split.value * 100)}%
            </span>
          </span>
        {/each}
      </div>
    {/if}

    <ol class="list-decimal list-inside flex flex-col gap-2 text-sm">
      <li class="ml-4">
        Open the <a href={dataset_link} class="link" target="_blank"
          >dataset page</a
        > in a new tab so you can follow these instructions.
      </li>
      <li class="ml-4">
        Using the "Select" button, select the data you want to use for one of
        the tags above. You can select many examples at once using the shift
        key.
      </li>
      <li class="ml-4">
        Click the "Tag" button, select "Add Tag", then add the desired tag.
      </li>
      <li class="ml-4">Repeat steps 2-3 for each tag.</li>
    </ol>
  </div>
</Dialog>
