import { defineConfig } from "tsup"

export default defineConfig([
  {
    entry: {
      index: "src/main/index.ts",
    },
    outDir: "dist/main",
    format: ["cjs"],
    platform: "node",
    target: "node18",
    sourcemap: true,
    clean: true,
    outExtension: () => ({ js: ".cjs" }),
    external: ["electron"],
  },
  {
    entry: {
      index: "src/preload/index.ts",
    },
    outDir: "dist/preload",
    format: ["cjs"],
    platform: "node",
    target: "node18",
    sourcemap: true,
    clean: false,
    outExtension: () => ({ js: ".cjs" }),
    external: ["electron"],
  },
])
