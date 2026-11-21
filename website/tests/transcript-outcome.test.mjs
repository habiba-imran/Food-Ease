import { test } from 'node:test';
import assert from 'node:assert/strict';
import { TranscriptView } from '../static/js/transcripts.mjs';

function fixture() {
  const container = { scrollHeight: 0, scrollTop: 0, clientHeight: 20, children: [],
    append(row) { this.children.push(row); },
    ownerDocument: {createElement() { return {dataset:{}, remove(){}}; }},
  };
  const view = new TranscriptView(container);
  return {container, view};
}
test('provider failures get a distinct terminal caption and cannot regress to partial text', () => {
  const {container, view} = fixture();
  const caption = {kind:'assistant', turnId:'turn', utteranceId:'speech', text:''};
  assert.equal(view.update({...caption, phase:'failed'}), true);
  assert.equal(container.children[0].dataset.phase, 'failed');
  assert.match(container.children[0].textContent, /جواب مکمل نہیں ہو سکا/);
  assert.doesNotMatch(container.children[0].textContent, /interrupted/);
  assert.equal(view.update({...caption, text:'late partial', phase:'updated'}), false);
});
test('genuine interruption preserves its label and partial spoken text', () => {
  const {container, view} = fixture();
  view.update({kind:'assistant', turnId:'turn', utteranceId:'speech', text:'آپ کے کارٹ', phase:'interrupted'});
  assert.equal(container.children[0].textContent, 'آپ کے کارٹ (interrupted)');
});
