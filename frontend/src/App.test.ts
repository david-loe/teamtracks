import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import App from "./App.vue";
import { router } from "./router";

describe("App", () => {
  it("renders the application shell", async () => {
    router.push("/songs");
    await router.isReady();

    const wrapper = mount(App, {
      global: {
        plugins: [createPinia(), router],
      },
    });

    expect(wrapper.text()).toContain("TeamTracks");
    expect(wrapper.text()).toContain("Songs");
    expect(wrapper.text()).toContain("Einstellungen");
  });
});
