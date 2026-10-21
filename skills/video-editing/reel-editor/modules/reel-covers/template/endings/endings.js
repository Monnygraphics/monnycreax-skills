// One ending per video. id = output name. next = "Up next" title (omit on the last one to show the follow line).
// Never read the full videos: ffprobe one for size/fps if unsure (template is 1080x1920 @ 30fps).
window.ENDINGS = [
  { id: "01-example", file: "Video 1.mp4", next: "Title of Video 2" },
  { id: "02-example", file: "Video 2.mp4" },
];
window.ENDCARD = {
  tagline: "Brand tagline here.", // script line; use the client's own big idea wording
  follow: "Follow for more",
  duration: 4.5, // seconds (3 to 5)
};
