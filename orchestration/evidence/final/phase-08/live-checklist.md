# Phase 8 live checks still required

Status: **not run**. No provider charges, physical recordings, listener ratings,
vendor outages or audible timing samples were produced by the offline verifier.
This is a validation checklist for Phase 8, not a claim of Phase 9 acceptance.

Use the production website, session service, worker and real three-seat LiveKit
room, with authorized provider usage. Keep recording disabled. Use fictional carts.
Record date, installed versions, browser/device, network and whether output really
reached the speaker/headphones. Never log tokens, keys, checkout authorization or
raw provider exception messages. Preserve submitted actions while interrupting speech.

1. Cause a controlled real STT connection failure after joining. Verify capture
   stops, existing cart survives and a typed request gets a grounded reply.
2. Repeat with real TTS failure. Verify no recursive spoken warning or silent
   claim of audible delivery; typing/manual remain usable. Restart explicitly
   before enabling speech again.
3. Cause a real model failure. Verify no further tool admission, local assistance
   ends and manual cart/checkout still work where the website remains reachable.
4. Interrupt network access for one seat, then both. Change the page manually
   while reconnecting. Verify fresh context, stale confirmation/reference rejection,
   current mode, one dispatch and no repeated mutation. Test longer than 15 seconds.
5. Disconnect app/user/agent seats, expire credentials, background the actual tab,
   duplicate the tab and reload. Verify ended tracks, detached output, cleanup
   ownership and explicit restart. Repeat with cleanup temporarily unavailable.
6. Lose responses after committed add and checkout, including a genuine RPC timeout.
   Verify one authoritative write/receipt by original ID. For not-seen, pending,
   expired and service-restart outcomes verify honest uncertainty and no retry.
7. Interrupt greeting, description, summary and reply with stop/correction. Include
   brief backchannels/background noise. Compare audible stop with the input onset
   using a common measurement clock. SDK interruption callback time alone is not
   evidence of audible silence. Recheck committed cart effects and final quantities.
8. Fill the adjacent CSV only from observations. Mark unmeasurable cases as such;
   do not insert zero latency or infer success from lack of audio. Report sample
   size, misses and false interruptions. Joint Phase 9 acceptance later requires
   at least 10 genuine interruption samples and its separate broader turn campaign.

Current sample counts: vendor outages 0; audible barge-in samples 0; human false
interruption judgments 0. The live part of the Phase 8 gate remains open.
