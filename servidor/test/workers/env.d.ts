import type { Env as EnvSino } from "../../src/objetos";

declare global {
  namespace Cloudflare {
    interface Env extends EnvSino {}
    interface GlobalProps {
      mainModule: typeof import("../../src/index");
    }
  }
}
