import { build } from "esbuild";

await build({
  stdin: { contents: 'export { Room, RoomEvent, Track, LocalAudioTrack } from "livekit-client";',
           resolveDir: process.cwd() },
  bundle: true, format: "esm", platform: "browser", target: "es2022", minify: true,
  legalComments: "eof", outfile: "static/vendor/livekit-client.2.15.4.mjs",
});
