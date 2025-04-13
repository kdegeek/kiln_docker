<script lang="ts">
  type OptionGroup = {
    label: string
    options: Option[]
  }
  type Option = {
    label: string
    value: string
    description?: string
  }

  export let options: [string, [string, string][]][] = []
  export let selected: string

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
  } // Watch for changes to options and recheck scrollability
  $: options, setTimeout(checkIfScrollable, 0)
</script>

<div class="dropdown w-full relative">
  <div
    tabindex="0"
    role="button"
    class="select select-bordered w-full flex items-center"
  >
    <span class="truncate">
      {(() => {
        const flatOptions = options.flatMap((group) => group[1])
        const selectedOption = flatOptions.find((item) => item[0] === selected)
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
            <button on:click={() => (selected = item[0])}>{item[1]}</button>
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
