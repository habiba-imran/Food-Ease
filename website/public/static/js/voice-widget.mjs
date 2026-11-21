// One persistent corner widget; it never creates a second conversation surface.
export class VoiceWidget {
  constructor({ element, panel, launcher }) {
    Object.assign(this, { element, panel, launcher });
    this.home = element.ownerDocument.createComment('Zara widget home');
    element.before(this.home);
    element.addEventListener('keydown', event => {
      if (event.key === 'Escape' && this.expanded) {
        event.preventDefault();
        event.stopPropagation();
        this.hide();
      }
    });
  }
  get expanded() { return !this.panel.hidden; }
  show() { this.panel.hidden = false; this.launcher.setAttribute('aria-expanded', 'true'); }
  hide() {
    const focused = this.panel.contains(this.panel.ownerDocument.activeElement);
    this.panel.hidden = true;
    this.launcher.setAttribute('aria-expanded', 'false');
    if (focused) this.launcher.focus({ preventScroll: true });
  }
  place() {
    // Native shopping dialogs make outside controls inert. Move this SAME widget
    // into their existing slot, keeping voice controls and transcript together.
    const slots = this.element.ownerDocument.querySelectorAll('dialog[open] [data-voice-launcher-slot]');
    const slot = Array.from(slots).at(-1);
    if (slot && this.element.parentElement !== slot) slot.append(this.element);
    else if (!slot && this.element.previousSibling !== this.home) this.home.after(this.element);
  }
}
