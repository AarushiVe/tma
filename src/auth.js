import { reactive } from 'vue'

export const auth = reactive({
  token: localStorage.getItem('trekison_token'),
  user: JSON.parse(localStorage.getItem('trekison_user') || 'null'),
})

export function setSession(token, user) {
  auth.token = token
  auth.user = user
  localStorage.setItem('trekison_token', token)
  localStorage.setItem('trekison_user', JSON.stringify(user))
}

export function updateUser(user) {
  auth.user = user
  localStorage.setItem('trekison_user', JSON.stringify(user))
}

export function logout() {
  auth.token = null
  auth.user = null
  localStorage.removeItem('trekison_token')
  localStorage.removeItem('trekison_user')
}

export function homePath(role = auth.user?.role) {
  return { admin: '/admin', staff: '/staff', trekker: '/trekker' }[role] || '/login'
}
