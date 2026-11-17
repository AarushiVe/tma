import { reactive } from 'vue'

// small messages shown at the top right of the screen
export const messages = reactive([])

export function toast(text, type = 'success') {
  const msg = { id: Date.now() + Math.random(), text, type }
  messages.push(msg)
  setTimeout(() => {
    const i = messages.indexOf(msg)
    if (i >= 0) messages.splice(i, 1)
  }, 3500)
}

export function toastError(err) {
  toast(err.message || 'Something went wrong', 'danger')
}
