# Sample dialogue (full order + correction)

Text-mode illustration against MockAdapter. Spoken form only — no IDs/JSON.

**User:** I’m hungry.  
**Agent:** I can suggest a few options. Prefer something light, spicy, or under a budget?

**User:** Vegetarian under eight hundred.  
**Agent:** Here is what I found: Veggie Wrap at 500 rupees; Masala Fries at 250 rupees. Want one of these?

**User:** Add the wrap.  
**Agent:** Updated. You have 1 Veggie Wrap. Total 500 rupees.

**User:** Actually make it two.  
**Agent:** Updated. You have 2 Veggie Wrap. Total 1000 rupees.

**User:** Wait — make it one.  
**Agent:** Updated. You have 1 Veggie Wrap. Total 500 rupees.

**User:** Checkout.  
**Agent:** Your demo total is 500 rupees. Shall I place the demo order?

**User:** Yes.  
**Agent:** Demo order placed. No real payment was taken.

Correction variant (wrong item):

**User:** Add the Zinger.  
**Agent:** Which one did you mean? Say the name or the first or second.  
**User:** The wrap.  
**Agent:** Updated. You have 1 Hot Chicken Wrap. Total 600 rupees.
