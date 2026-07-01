// Registra os matchers customizados do @testing-library/jest-dom globalmente.
// Ex.: expect(el).toBeInTheDocument(), .toHaveTextContent(), .toBeDisabled(), etc.
import '@testing-library/jest-dom'

// Polyfill para HTMLDialogElement.showModal() e .close() em jsdom
// (jsdom 26.1.0 não implementa esses métodos nativamente)
if (typeof window !== 'undefined' && window.HTMLDialogElement) {
  if (!window.HTMLDialogElement.prototype.showModal) {
    window.HTMLDialogElement.prototype.showModal = jest.fn(function () {
      this.open = true
    })
  }
  if (!window.HTMLDialogElement.prototype.close) {
    window.HTMLDialogElement.prototype.close = jest.fn(function () {
      this.open = false
    })
  }
  if (!window.HTMLDialogElement.prototype.show) {
    window.HTMLDialogElement.prototype.show = jest.fn(function () {
      this.open = true
    })
  }
}
