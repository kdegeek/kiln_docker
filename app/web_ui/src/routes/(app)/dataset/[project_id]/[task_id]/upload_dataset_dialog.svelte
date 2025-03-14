<script lang="ts">
  import { client } from "$lib/api_client"
  import { KilnError, createKilnError } from "$lib/utils/error_handlers"
  import { page } from "$app/stores"
  import Dialog from "$lib/ui/dialog.svelte"

  export let onImportCompleted: () => void

  let error: KilnError | null = null
  let loading = false
  let selected_file: File | null = null

  $: project_id = $page.params.project_id
  $: task_id = $page.params.task_id

  function handleFileSelect(event: Event) {
    const input = event.target as HTMLInputElement
    if (input.files && input.files[0]) {
      selected_file = input.files[0]
    }
  }

  async function handleUpload(): Promise<boolean> {
    if (!selected_file) {
      return false
    }

    loading = true
    try {
      const formData = new FormData()
      formData.append("file", selected_file)

      const { error } = await client.POST(
        "/api/projects/{project_id}/tasks/{task_id}/runs/bulk_upload",
        {
          params: { path: { project_id, task_id } },

          // todo: a transform must be set up to determine how to serialize multipart file uploads
          // see: https://github.com/openapi-ts/openapi-typescript/issues/1214
          body: formData as unknown as { file: string },
        },
      )

      if (error) {
        throw error
      }

      selected_file = null

      onImportCompleted()

      return true
    } catch (e) {
      error = createKilnError(e)
      return false
    } finally {
      loading = false
    }
  }

  let dialog: Dialog | null = null

  export function show() {
    dialog?.show()
    selected_file = null
  }

  export function close() {
    dialog?.close()
    selected_file = null
    error = null
    loading = false
    return true
  }

  function handleCancel() {
    close()
    return true
  }
</script>

<Dialog
  bind:this={dialog}
  title="Upload CSV to Dataset"
  action_buttons={[
    { label: "Cancel", isCancel: true, action: () => handleCancel() },
    {
      label: "Upload",
      asyncAction: () => handleUpload(),
      disabled: !selected_file,
    },
  ]}
>
  <div class="font-light text-sm">
    {#if loading}
      <div class="w-full min-h-[50vh] flex justify-center items-center">
        <div class="loading loading-spinner loading-lg"></div>
      </div>
    {:else}
      <div class="space-y-2">
        <div>
          <p>
            Upload a CSV to add each row to your dataset. The CSV must have a
            header row. The following columns are supported:
          </p>
          <ul class="mb-4 ml-4 mt-1 list-disc">
            <li><code>input</code> - Required</li>
            <li><code>output</code> - Required</li>
            <li><code>reasoning</code> - Optional</li>
            <li><code>tags</code> - Optional, comma separated string</li>
          </ul>
          <p class="mb-4">
            See an example <a
              href="#link-to-example-on-github"
              target="_blank"
              class="link">an example CSV</a
            >.
          </p>
        </div>
      </div>
      <input
        type="file"
        class="file-input file-input-bordered w-full"
        on:change={handleFileSelect}
        accept=".csv"
      />
    {/if}
  </div>
  {#if error}
    <div class="pt-2 text-error text-sm">
      {error.getMessage() || "An unknown error occurred"}
    </div>
  {/if}
</Dialog>
