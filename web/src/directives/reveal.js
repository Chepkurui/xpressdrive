// v-reveal: fades/slides an element in the first time it scrolls into view.
// Optional value = delay in ms, e.g. v-reveal="150" to stagger items.
const io =
  typeof window !== 'undefined' && 'IntersectionObserver' in window
    ? new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (e.isIntersecting) {
              e.target.classList.add('in')
              io.unobserve(e.target)
            }
          }
        },
        { threshold: 0, rootMargin: '0px 0px -8% 0px' },
      )
    : null

export default {
  mounted(el, binding) {
    el.classList.add('reveal')
    if (binding.value) el.style.setProperty('--reveal-delay', `${Number(binding.value) || 0}ms`)
    if (io) io.observe(el)
    else el.classList.add('in')
  },
  unmounted(el) {
    io?.unobserve(el)
  },
}
