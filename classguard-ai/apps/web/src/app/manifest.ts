import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "ClassGuard AI",
    short_name: "ClassGuard",
    description:
      "Institution setup, classroom planning, and student enrollment.",
    start_url: "/",
    display: "standalone",
    background_color: "#f6f8f7",
    theme_color: "#0b6253",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
  };
}
