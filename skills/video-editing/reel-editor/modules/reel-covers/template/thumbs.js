// One entry per cover. style "arch" = cutout on brand arch (needs cutouts/<photo>.png),
// "full" = full-bleed photo + type. theme "light"/"dark": alternate them for a checkerboard grid.
// photo = file name in photos/ without .jpg. line1 = bold line, line2 = script line.
window.THUMBS = [
  { id: "01-example", ep: 1, style: "arch", theme: "light", photo: "PHOTO_NAME", line1: "Bold Line", line2: "script line" },
  { id: "02-example", style: "full", theme: "dark", photo: "PHOTO_NAME", kicker: "Myth or Fact?", line1: "Bold Line", line2: "script line", accent: "?" },
];
